"""Tests for SQLite-backed FastAPI service.

All original behaviour is preserved; the fixture now creates a temporary
SQLite database instead of a JSON file.
"""
import re
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.parsing import due_date, match_farm, normalize_name, parse_note


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(tmp_path / "visits.db"))


def save(client, raw="", visit_date="2026-11-01"):
    response = client.post("/notes", json={"raw_text": raw, "visit_date": visit_date})
    assert response.status_code == 201, response.text
    return response.json()


def farm(client, name):
    response = client.post("/farms", json={"name": name})
    assert response.status_code == 201
    return response.json()


# ---------------------------------------------------------------------------
# Req 2: Verbatim storage
# ---------------------------------------------------------------------------

def test_save_before_parse_failure_and_restart(client, monkeypatch):
    """raw_text must be persisted BEFORE parsing is attempted (Req 2)."""
    raw = "  কৃষক: রহিম\r\nUnrecognized text!  "

    def fail(text, visit_date):
        # At this point the DB row must already exist with the raw text
        import sqlite3
        db_path = client.app.state.db_path
        con = sqlite3.connect(str(db_path))
        row = con.execute("SELECT raw_text, parse_status FROM visits").fetchone()
        con.close()
        assert row is not None, "Row must exist before parse"
        assert row[0] == raw
        assert row[1] == "pending"
        raise ValueError("parser unavailable")

    monkeypatch.setattr("backend.main.parse_note", fail)
    note = save(client, raw)
    assert note["parse_status"] == "failed"

    # Restart with same DB
    restarted = TestClient(create_app(client.app.state.db_path))
    assert restarted.get("/notes/" + note["id"]).json()["raw_text"] == raw


@pytest.mark.parametrize("raw", ["", "   ", "unstructured words", "শুধু কিছু কথা"])
def test_optional_fields_never_reject_content(client, raw):
    note = save(client, raw)
    assert note["raw_text"] == raw
    assert note["parsed"]["farmer"] is None


def test_raw_text_never_altered(client):
    """PATCH must not change raw_text (Req 2)."""
    note = save(client, "  Problem: spots\nFollow-up: next week  ")
    url = "/notes/" + note["id"]
    # raw_text field is not in Correction model → 422
    assert client.patch(url, json={"raw_text": "changed"}).status_code == 422
    corrected = client.patch(url, json={"problem": "yellow leaves", "follow_up": "in two weeks"}).json()
    assert corrected["raw_text"] == note["raw_text"]
    assert corrected["parsed"]["problem"] == "yellow leaves"
    assert corrected["parsed"]["due_date"] == "2026-11-15"
    assert client.patch(url, json={"follow_up": None}).json()["parsed"]["due_date"] is None


# ---------------------------------------------------------------------------
# Req 3: Farm identity
# ---------------------------------------------------------------------------

def test_matching_three_outcomes_and_alias_learning(client):
    rahim = farm(client, "Abdul Rahim")
    confident = save(client, "Farmer: ABDUL RAHIM Miah")
    assert confident["match"]["status"] == "confident_match"

    farm(client, "Abdul Karim")
    uncertain = save(client, "Farmer: Abdul Rarim")
    assert uncertain["match"]["status"] == "uncertain"
    assert uncertain["farm_id"] is None
    assert len(uncertain["match"]["candidates"]) == 2

    unknown = save(client, "Farmer: Zzzzzzz")
    assert unknown["match"]["status"] == "no_match"

    response = client.post(
        "/notes/" + unknown["id"] + "/confirm-farm",
        json={"farm_id": rahim["id"]},
    )
    assert response.json()["farm_confirmed"]

    # Alias learned → next visit matches confidently
    next_note = save(client, "Farmer: Zzzzzzz")
    assert next_note["farm_id"] == rahim["id"]

    # Alias appears in farm's alias list
    farms = client.get("/farms").json()
    rahim_returned = next(f for f in farms if f["id"] == rahim["id"])
    alias_texts = [a["alias"] for a in rahim_returned["aliases"]]
    assert "Zzzzzzz" in alias_texts


def test_duplicate_names_are_uncertain():
    farms_list = [{"id": str(i), "name": "Rahim", "aliases": []} for i in range(2)]
    assert match_farm("Rahim bhai", farms_list)["status"] == "uncertain"
    assert normalize_name("Mohammed Rehman MIA") == normalize_name("Muhammad Rahman bhai")


# ---------------------------------------------------------------------------
# Req 1 & 6: Parsed fields + match_status
# ---------------------------------------------------------------------------

def test_extract_all_fields():
    parsed = parse_note(
        "Farmer: Rahim Mia; Plot: north; Crop: rice; Problem: leaf spots; "
        "Advice: reduce watering; Follow-up: in two weeks",
        "2026-11-01",
    )
    assert parsed == {
        "farmer": "Rahim Mia", "plot": "north", "crop": "rice",
        "problem": "leaf spots", "advice": "reduce watering",
        "follow_up": "in two weeks", "due_date": "2026-11-15", "no_problem": False,
    }


def test_bangla_labels_and_date():
    parsed = parse_note(
        "কৃষক: রহিম; ফসল: ধান; সমস্যা: পোকা; পরামর্শ: পানি কমান; ফলোআপ: দুই সপ্তাহ পরে",
        "2026-11-01",
    )
    assert parsed["farmer"] == "রহিম"
    assert parsed["due_date"] == "2026-11-15"


def test_match_status_in_visit(client):
    """match_status field must reflect matched/needs_confirmation/unmatched (Req 1 & 6)."""
    farm(client, "Rahim")
    matched = save(client, "Farmer: Rahim")
    assert matched["match_status"] == "matched"

    farm(client, "Karim")
    uncertain = save(client, "Farmer: Rahirm")   # typo → uncertain
    assert uncertain["match_status"] == "needs_confirmation"

    unmatched = save(client, "Farmer: Zzzzzzz")
    assert unmatched["match_status"] == "unmatched"


# ---------------------------------------------------------------------------
# Req 4: Follow-ups
# ---------------------------------------------------------------------------

def test_followups_completion_history_and_reassignment(client):
    first_farm = farm(client, "Rahim")
    other_farm = farm(client, "Karim")
    first = save(client, "Farmer: Rahim; Follow-up: next week")
    save(client, "Farmer: Karim; Follow-up: next week")
    unknown_date = save(client, "Follow-up: check when possible")

    buckets = client.get("/followups?as_of=2026-11-09").json()
    assert len(buckets["overdue"]) == 2
    assert buckets["undated"][0]["note_id"] == unknown_date["id"]

    new = save(client, "Farmer: Rahim; Follow-up: in two weeks", "2026-11-10")
    buckets = client.get("/followups?as_of=2026-11-10").json()
    assert buckets["completed"][0]["note_id"] == first["id"]
    assert buckets["completed"][0]["completed_by"] == new["id"]
    assert buckets["upcoming"][0]["note_id"] == new["id"]

    assert client.get("/farms/" + first_farm["id"] + "/last-visit").json()["id"] == new["id"]
    assert len(client.get("/farms/" + first_farm["id"] + "/history").json()) == 2

    # Reassign follow-up note to other farm → first note no longer completed
    client.post("/notes/" + new["id"] + "/confirm-farm", json={"farm_id": other_farm["id"]})
    assert client.get("/notes/" + first["id"]).json()["completed_by"] is None


def test_backdated_visit_and_same_day_order(client):
    farm(client, "Rahim")
    later   = save(client, "Farmer: Rahim", "2026-11-20")
    earlier = save(client, "Farmer: Rahim; Follow-up: next week", "2026-11-01")
    assert earlier["completed_by"] == later["id"]

    same_day = save(client, "Farmer: Rahim; Follow-up: tomorrow", "2026-11-20")
    assert same_day["completed_by"] is None

    next_note = save(client, "Farmer: Rahim", "2026-11-20")
    assert client.get("/notes/" + same_day["id"]).json()["completed_by"] == next_note["id"]


# ---------------------------------------------------------------------------
# Req 5 & 6: Queries + performance (views exercised via API)
# ---------------------------------------------------------------------------

def test_reports_use_stored_data_include_no_problem_and_empty(client, monkeypatch):
    farm(client, "Rahim")
    save(client, "Farmer: Rahim; No problem.")
    save(client, "Farmer: Rahim; Problem: spots; Advice: less water")
    save(client)
    save(client, "Problem: outside month", "2026-10-31")

    monkeypatch.setattr(
        "backend.main.parse_note",
        lambda *args: pytest.fail("Report must never reparse"),
    )
    report = client.get("/reports?month=2026-11").json()
    assert report["total_visits"] == 3
    assert report["no_problem_count"] == 1
    assert report["unique_farms"] == 1
    assert report["problems"][0]["text"] == "spots"
    assert report["advice"][0]["text"] == "less water"
    assert client.get("/reports?month=2026-13").status_code == 422
    assert client.get("/reports?month=0000-01").status_code == 422


def test_farm_history_view(client):
    """v_farm_history view exercised via /farms/{id}/history endpoint."""
    f = farm(client, "Rahim")
    save(client, "Farmer: Rahim; Problem: spots", "2026-11-01")
    save(client, "Farmer: Rahim; Advice: less water", "2026-11-10")
    history = client.get(f"/farms/{f['id']}/history").json()
    assert len(history) == 2
    # Most recent first
    assert history[0]["visit_date"] >= history[1]["visit_date"]


def test_monthly_counts_view(client):
    """v_monthly_counts view exercised via /reports endpoint."""
    farm(client, "Rahim")
    farm(client, "Karim")
    save(client, "Farmer: Rahim; No problem.", "2026-11-01")
    save(client, "Farmer: Karim; Problem: rust", "2026-11-05")
    save(client, "Farmer: Unknown")  # unmatched
    report = client.get("/reports?month=2026-11").json()
    assert report["total_visits"] == 3
    assert report["distinct_farms"] == 2 or report["unique_farms"] == 2
    assert report["no_problem_count"] == 1


# ---------------------------------------------------------------------------
# General / infra
# ---------------------------------------------------------------------------

def test_api_prefix_cors_and_not_found(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/notes/missing").status_code == 404
    assert client.get("/farms/missing/history").status_code == 404
    created = farm(client, "No visits")
    assert client.get("/farms/" + created["id"] + "/last-visit").json() is None
    response = client.options(
        "/api/notes",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_concurrent_saves_are_not_lost(client):
    with ThreadPoolExecutor(max_workers=6) as pool:
        notes = list(pool.map(lambda i: save(client, str(i)), range(12)))
    import sqlite3
    con = sqlite3.connect(str(client.app.state.db_path))
    count = con.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    con.close()
    assert len({n["id"] for n in notes}) == count == 12


def test_owner_farm_snapshot_and_selected_farm(client):
    registered = client.post(
        "/farms",
        json={"name": "Green Farm", "owner_name": "Rahim Mia", "location": "North village"},
    ).json()
    note = client.post(
        "/notes",
        json={
            "raw_text":  "No problem.",
            "farm_id":   registered["id"],
            "farm_info": {
                "owner_name": "Rahim Mia",
                "farm_name":  "Green Farm",
                "plot":       "A",
                "crop":       "rice",
            },
        },
    ).json()
    assert note["farm_id"] == registered["id"]
    assert note["farm_confirmed"]
    assert note["parsed"]["plot"] == "A"
    assert note["raw_text"] == "No problem."
    assert save(client, "Farmer: Rahim bhai")["farm_id"] == registered["id"]


def test_bangla_normalization_preserves_vowels():
    assert normalize_name("রহিম ভাই") == normalize_name("রহিম")
    assert normalize_name("করিম") != normalize_name("কারিম")


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("in two weeks",       "2026-11-15"),
        ("next week",          "2026-11-08"),
        ("tomorrow",           "2026-11-02"),
        ("in 3 days",          "2026-11-04"),
        ("next month",         "2026-12-01"),
        ("day after tomorrow", "2026-11-03"),
        ("2026-12-05",         "2026-12-05"),
        ("when possible",      None),
    ],
)
def test_relative_dates(phrase, expected):
    assert due_date(phrase, "2026-11-01") == expected
