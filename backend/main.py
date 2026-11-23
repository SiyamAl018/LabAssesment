"""Single-process FastAPI service with atomic JSON-file storage (no database)."""
import copy
import json
import logging
import os
import re
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from .parsing import FIELDS, due_date, match_farm, normalize_name, parse_note

logger = logging.getLogger(__name__)


def today():
    return datetime.now(timezone(timedelta(hours=6))).date()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.data = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {'notes': [], 'farms': []}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        try:
            with temporary.open('w', encoding='utf-8', newline='') as output:
                json.dump(self.data, output, ensure_ascii=False, indent=2)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
        except Exception:
            # Roll memory back to the last durable snapshot if a write fails.
            self.data = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {'notes': [], 'farms': []}
            raise

    def get(self, kind, identifier):
        item = next((item for item in self.data[kind] if item['id'] == identifier), None)
        if item is None:
            raise HTTPException(404, f'{kind[:-1].capitalize()} not found')
        return item


class FarmInfo(BaseModel):
    owner_name: str | None = None
    farm_name: str | None = None
    location: str | None = None
    plot: str | None = None
    crop: str | None = None


class NoteInput(BaseModel):
    raw_text: str = ''
    visit_date: date = Field(default_factory=today)
    farm_id: str | None = None
    farm_info: FarmInfo = Field(default_factory=FarmInfo)


class Correction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    farmer: str | None = None
    plot: str | None = None
    crop: str | None = None
    problem: str | None = None
    advice: str | None = None
    follow_up: str | None = None
    due_date: date | None = None
    no_problem: bool | None = None


class FarmInput(BaseModel):
    name: str = Field(min_length=1)
    owner_name: str | None = None
    location: str | None = None


class FarmConfirmation(BaseModel):
    # null explicitly leaves the note unmatched.
    farm_id: str | None = None
    alias: str | None = None


def reconcile(data):
    """Rebuild stored completion links after assignment/correction, including backdated visits."""
    notes = sorted(data['notes'], key=lambda n: (n['visit_date'], n['sequence']))
    for index, note in enumerate(notes):
        next_visit = next((n for n in notes[index + 1:] if note['farm_id'] and n['farm_id'] == note['farm_id']), None)
        note['completed_by'] = next_visit['id'] if next_visit and note['parsed'].get('follow_up') else None


def create_app(data_path=None):
    app = FastAPI(title='Farm visit notes', version='1.0.0')
    app.add_middleware(CORSMiddleware, allow_origins=os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','), allow_methods=['GET', 'POST', 'PATCH'], allow_headers=['Content-Type'])
    store = Store(data_path or os.environ.get('NOTES_FILE', str(Path(__file__).parent / 'data' / 'notes.json')))
    app.state.store = store
    router = APIRouter()

    @router.get('/health')
    def health():
        return {'status': 'ok', 'storage': 'json-file'}

    @router.post('/notes', status_code=201)
    def create_note(body: NoteInput):
        with store.lock:
            note = {'id': str(uuid4()), 'sequence': len(store.data['notes']) + 1,
                    'raw_text': body.raw_text, 'visit_date': body.visit_date.isoformat(),
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'farm_info': body.farm_info.model_dump(),
                    'parsed': {**dict.fromkeys(FIELDS), 'due_date': None, 'no_problem': None},
                    'parse_status': 'pending', 'farm_id': None, 'farm_confirmed': False,
                    'match': {'status': 'no_match', 'farm_id': None, 'candidates': []}, 'completed_by': None}
            store.data['notes'].append(note)
            store.save()  # Raw text is durable BEFORE any parser or matching code runs.
            try:
                note['parsed'] = parse_note(body.raw_text, note['visit_date'])
                for field, value in {'farmer': body.farm_info.owner_name, 'plot': body.farm_info.plot, 'crop': body.farm_info.crop}.items():
                    if value:
                        note['parsed'][field] = value
                note['match'] = match_farm(body.farm_info.farm_name or note['parsed']['farmer'], store.data['farms'])
                note['farm_id'] = note['match']['farm_id']
                note['parse_status'] = 'parsed'
                reconcile(store.data)
            except Exception:
                logger.exception('Parsing failed for saved note %s', note['id'])
                note['parse_status'] = 'failed'
            # A selected farm is an explicit decision, independent of parsing success.
            selected = next((f for f in store.data['farms'] if f['id'] == body.farm_id), None)
            if selected:
                note['farm_id'] = selected['id']
                note['farm_confirmed'] = True
                note['match'] = {'status': 'confident_match', 'farm_id': selected['id'], 'candidates': []}
                for key, value in {'owner_name': selected.get('owner_name'), 'farm_name': selected['name'], 'location': selected.get('location')}.items():
                    if not note['farm_info'].get(key):
                        note['farm_info'][key] = value
            reconcile(store.data)
            store.save()
            return copy.deepcopy(note)

    @router.get('/notes/{note_id}')
    def get_note(note_id: str):
        with store.lock:
            return copy.deepcopy(store.get('notes', note_id))

    @router.patch('/notes/{note_id}')
    def correct_note(note_id: str, body: Correction):
        with store.lock:
            note = store.get('notes', note_id)
            changes = body.model_dump(exclude_unset=True, mode='json')
            note['parsed'].update(changes)
            if 'follow_up' in changes and 'due_date' not in changes:
                note['parsed']['due_date'] = due_date(changes['follow_up'], note['visit_date'])
            if 'problem' in changes and 'no_problem' not in changes:
                # A correction invalidates the old classification; do not infer no-problem from emptiness.
                note['parsed']['no_problem'] = None
            if 'farmer' in changes:
                note['farm_confirmed'] = False
                note['match'] = match_farm(changes['farmer'], store.data['farms'])
                note['farm_id'] = note['match']['farm_id']
            reconcile(store.data)
            store.save()
            return copy.deepcopy(note)

    @router.post('/notes/{note_id}/confirm-farm')
    def confirm_farm(note_id: str, body: FarmConfirmation):
        with store.lock:
            note = store.get('notes', note_id)
            if body.farm_id:
                farm = store.get('farms', body.farm_id)
                alias = body.alias if body.alias is not None else note.get('farm_info', {}).get('farm_name') or note['parsed']['farmer']
                if alias and normalize_name(alias) and alias not in farm['aliases']:
                    farm['aliases'].append(alias)
            note['farm_id'] = body.farm_id
            note['farm_confirmed'] = True
            note['match'] = {'status': 'confident_match' if body.farm_id else 'no_match', 'farm_id': body.farm_id, 'candidates': []}
            reconcile(store.data)
            store.save()
            return copy.deepcopy(note)

    @router.get('/farms')
    def farms():
        with store.lock:
            return copy.deepcopy(store.data['farms'])

    @router.post('/farms', status_code=201)
    def create_farm(body: FarmInput):
        if not body.name.strip():
            raise HTTPException(422, 'Farm name cannot be blank')
        with store.lock:
            farm = {'id': str(uuid4()), 'name': body.name, 'owner_name': body.owner_name, 'location': body.location, 'aliases': []}
            store.data['farms'].append(farm)
            store.save()
            return copy.deepcopy(farm)

    def history(farm_id):
        store.get('farms', farm_id)
        return sorted((n for n in store.data['notes'] if n['farm_id'] == farm_id), key=lambda n: (n['visit_date'], n['sequence']), reverse=True)

    @router.get('/farms/{farm_id}/history')
    def farm_history(farm_id: str):
        with store.lock:
            return copy.deepcopy(history(farm_id))

    @router.get('/farms/{farm_id}/last-visit')
    def last_visit(farm_id: str):
        with store.lock:
            visits = history(farm_id)
            return copy.deepcopy(visits[0]) if visits else None

    @router.get('/followups')
    def followups(as_of: date | None = None):
        with store.lock:
            reference = (as_of or today()).isoformat()
            result = {'overdue': [], 'upcoming': [], 'undated': [], 'completed': []}
            for note in store.data['notes']:
                if not note['parsed']['follow_up']:
                    continue
                farm = next((f for f in store.data['farms'] if f['id'] == note['farm_id']), None)
                item = {'note_id': note['id'], 'farm_id': note['farm_id'], 'farm_name': farm['name'] if farm else None,
                        'follow_up': note['parsed']['follow_up'], 'due_date': note['parsed']['due_date'], 'completed_by': note['completed_by']}
                bucket = 'completed' if item['completed_by'] else 'undated' if not item['due_date'] else 'overdue' if item['due_date'] < reference else 'upcoming'
                result[bucket].append(item)
            for items in result.values():
                items.sort(key=lambda item: item['due_date'] or '9999')
            return copy.deepcopy(result)

    @router.get('/reports')
    def report(month: str = Query(..., pattern=r'^\d{4}-(0[1-9]|1[0-2])$')):
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', month) or month.startswith('0000'):
            raise HTTPException(422, 'Use a valid YYYY-MM month')
        with store.lock:
            notes = [n for n in store.data['notes'] if n['visit_date'].startswith(month)]
            return copy.deepcopy({'month': month, 'total_visits': len(notes),
                'unique_farms': len({n['farm_id'] for n in notes if n['farm_id']}),
                'unmatched_visits': sum(n['farm_id'] is None for n in notes),
                'no_problem_count': sum(n['parsed']['no_problem'] is True for n in notes),
                'problems': [{'note_id': n['id'], 'text': n['parsed']['problem']} for n in notes if n['parsed']['problem'] and n['parsed']['no_problem'] is not True],
                'advice': [{'note_id': n['id'], 'text': n['parsed']['advice']} for n in notes if n['parsed']['advice']], 'visits': notes})

    app.include_router(router)
    app.include_router(router, prefix='/api', include_in_schema=False)
    return app


app = create_app()
