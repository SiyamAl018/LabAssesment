import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.parsing import due_date, match_farm, normalize_name, parse_note


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(tmp_path / 'notes.json'))


def save(client, raw='', visit_date='2026-11-01'):
    response = client.post('/notes', json={'raw_text': raw, 'visit_date': visit_date})
    assert response.status_code == 201, response.text
    return response.json()


def farm(client, name):
    response = client.post('/farms', json={'name': name})
    assert response.status_code == 201
    return response.json()


def test_save_before_parse_failure_and_restart(client, monkeypatch):
    raw = '  কৃষক: রহিম\r\nUnrecognized text!  '
    def fail(text, visit_date):
        persisted = json.loads(client.app.state.store.path.read_text(encoding='utf-8'))
        assert persisted['notes'][0]['raw_text'] == raw
        assert persisted['notes'][0]['parse_status'] == 'pending'
        raise ValueError('parser unavailable')
    monkeypatch.setattr('backend.main.parse_note', fail)
    note = save(client, raw)
    assert note['parse_status'] == 'failed'
    restarted = TestClient(create_app(client.app.state.store.path))
    assert restarted.get('/notes/' + note['id']).json()['raw_text'] == raw


@pytest.mark.parametrize('raw', ['', '   ', 'unstructured words', 'শুধু কিছু কথা'])
def test_optional_fields_never_reject_content(client, raw):
    note = save(client, raw)
    assert note['raw_text'] == raw
    assert note['parsed']['farmer'] is None


def test_extract_all_fields():
    parsed = parse_note('Farmer: Rahim Mia; Plot: north; Crop: rice; Problem: leaf spots; Advice: reduce watering; Follow-up: in two weeks', '2026-11-01')
    assert parsed == {'farmer': 'Rahim Mia', 'plot': 'north', 'crop': 'rice', 'problem': 'leaf spots', 'advice': 'reduce watering', 'follow_up': 'in two weeks', 'due_date': '2026-11-15', 'no_problem': False}


def test_bangla_labels_and_date():
    parsed = parse_note('কৃষক: রহিম; ফসল: ধান; সমস্যা: পোকা; পরামর্শ: পানি কমান; ফলোআপ: দুই সপ্তাহ পরে', '2026-11-01')
    assert parsed['farmer'] == 'রহিম'
    assert parsed['due_date'] == '2026-11-15'


@pytest.mark.parametrize(('phrase', 'expected'), [('in two weeks', '2026-11-15'), ('next week', '2026-11-08'), ('tomorrow', '2026-11-02'), ('in 3 days', '2026-11-04'), ('next month', '2026-12-01'), ('day after tomorrow', '2026-11-03'), ('2026-12-05', '2026-12-05'), ('when possible', None)])
def test_relative_dates(phrase, expected):
    assert due_date(phrase, '2026-11-01') == expected


def test_corrections_cannot_mutate_raw(client):
    note = save(client, '  Problem: spots\nFollow-up: next week  ')
    url = '/notes/' + note['id']
    assert client.patch(url, json={'raw_text': 'changed'}).status_code == 422
    corrected = client.patch(url, json={'problem': 'yellow leaves', 'follow_up': 'in two weeks'}).json()
    assert corrected['raw_text'] == note['raw_text']
    assert corrected['parsed']['problem'] == 'yellow leaves'
    assert corrected['parsed']['due_date'] == '2026-11-15'
    assert client.patch(url, json={'follow_up': None}).json()['parsed']['due_date'] is None


def test_matching_three_outcomes_and_alias_learning(client):
    rahim = farm(client, 'Abdul Rahim')
    confident = save(client, 'Farmer: ABDUL RAHIM Miah')
    assert confident['match']['status'] == 'confident_match'
    farm(client, 'Abdul Karim')
    uncertain = save(client, 'Farmer: Abdul Rarim')
    assert uncertain['match']['status'] == 'uncertain'
    assert uncertain['farm_id'] is None
    assert len(uncertain['match']['candidates']) == 2
    unknown = save(client, 'Farmer: Zzzzzzz')
    assert unknown['match']['status'] == 'no_match'
    response = client.post('/notes/' + unknown['id'] + '/confirm-farm', json={'farm_id': rahim['id']})
    assert response.json()['farm_confirmed']
    assert save(client, 'Farmer: Zzzzzzz')['farm_id'] == rahim['id']
    assert 'Zzzzzzz' in client.get('/farms').json()[0]['aliases']


def test_duplicate_names_are_uncertain():
    farms = [{'id': str(i), 'name': 'Rahim', 'aliases': []} for i in range(2)]
    assert match_farm('Rahim bhai', farms)['status'] == 'uncertain'
    assert normalize_name('Mohammed Rehman MIA') == normalize_name('Muhammad Rahman bhai')


def test_followups_completion_history_and_reassignment(client):
    first_farm = farm(client, 'Rahim')
    other_farm = farm(client, 'Karim')
    first = save(client, 'Farmer: Rahim; Follow-up: next week')
    save(client, 'Farmer: Karim; Follow-up: next week')
    unknown_date = save(client, 'Follow-up: check when possible')
    buckets = client.get('/followups?as_of=2026-11-09').json()
    assert len(buckets['overdue']) == 2
    assert buckets['undated'][0]['note_id'] == unknown_date['id']
    new = save(client, 'Farmer: Rahim; Follow-up: in two weeks', '2026-11-10')
    buckets = client.get('/followups?as_of=2026-11-10').json()
    assert buckets['completed'][0]['note_id'] == first['id']
    assert buckets['completed'][0]['completed_by'] == new['id']
    assert buckets['upcoming'][0]['note_id'] == new['id']
    assert client.get('/farms/' + first_farm['id'] + '/last-visit').json()['id'] == new['id']
    assert len(client.get('/farms/' + first_farm['id'] + '/history').json()) == 2
    client.post('/notes/' + new['id'] + '/confirm-farm', json={'farm_id': other_farm['id']})
    assert client.get('/notes/' + first['id']).json()['completed_by'] is None


def test_backdated_visit_and_same_day_order(client):
    farm(client, 'Rahim')
    later = save(client, 'Farmer: Rahim', '2026-11-20')
    earlier = save(client, 'Farmer: Rahim; Follow-up: next week', '2026-11-01')
    assert earlier['completed_by'] == later['id']
    same_day = save(client, 'Farmer: Rahim; Follow-up: tomorrow', '2026-11-20')
    assert same_day['completed_by'] is None
    next_note = save(client, 'Farmer: Rahim', '2026-11-20')
    assert client.get('/notes/' + same_day['id']).json()['completed_by'] == next_note['id']


def test_reports_use_stored_data_include_no_problem_and_empty(client, monkeypatch):
    farm(client, 'Rahim')
    save(client, 'Farmer: Rahim; No problem.')
    save(client, 'Farmer: Rahim; Problem: spots; Advice: less water')
    save(client)
    save(client, 'Problem: outside month', '2026-10-31')
    monkeypatch.setattr('backend.main.parse_note', lambda *args: pytest.fail('Report must never reparse'))
    report = client.get('/reports?month=2026-11').json()
    assert report['total_visits'] == 3
    assert report['no_problem_count'] == 1
    assert report['unique_farms'] == 1
    assert report['problems'][0]['text'] == 'spots'
    assert report['advice'][0]['text'] == 'less water'
    assert client.get('/reports?month=2026-13').status_code == 422
    assert client.get('/reports?month=0000-01').status_code == 422


def test_api_prefix_cors_and_not_found(client):
    assert client.get('/api/health').status_code == 200
    assert client.get('/notes/missing').status_code == 404
    assert client.get('/farms/missing/history').status_code == 404
    created = farm(client, 'No visits')
    assert client.get('/farms/' + created['id'] + '/last-visit').json() is None
    response = client.options('/api/notes', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST'})
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'


def test_concurrent_saves_are_not_lost(client):
    with ThreadPoolExecutor(max_workers=6) as pool:
        notes = list(pool.map(lambda i: save(client, str(i)), range(12)))
    persisted = json.loads(client.app.state.store.path.read_text(encoding='utf-8'))
    assert len({n['id'] for n in notes}) == len(persisted['notes']) == 12


def test_owner_farm_snapshot_and_selected_farm(client):
    registered = client.post('/farms', json={'name': 'Green Farm', 'owner_name': 'Rahim Mia', 'location': 'North village'}).json()
    note = client.post('/notes', json={'raw_text': 'No problem.', 'farm_id': registered['id'], 'farm_info': {'owner_name': 'Rahim Mia', 'farm_name': 'Green Farm', 'plot': 'A', 'crop': 'rice'}}).json()
    assert note['farm_id'] == registered['id']
    assert note['farm_confirmed']
    assert note['farm_info']['location'] == 'North village'
    assert note['parsed']['farmer'] == 'Rahim Mia'
    assert note['parsed']['plot'] == 'A'
    assert note['raw_text'] == 'No problem.'
    assert save(client, 'Farmer: Rahim bhai')['farm_id'] == registered['id']
    assert client.get('/notes/' + note['id']).json()['farm_info']['farm_name'] == 'Green Farm'


def test_bangla_normalization_preserves_vowels():
    assert normalize_name('রহিম ভাই') == normalize_name('রহিম')
    assert normalize_name('করিম') != normalize_name('কারিম')

