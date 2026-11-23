"""SQLite database layer for farm visit notes.

Thread-safety: SQLite WAL mode + a per-connection check_same_thread=False.
Every public function opens a short-lived connection so the calling thread
owns the connection for the full duration of the operation, which is the
simplest correct approach for FastAPI with sync route handlers.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = Path(__file__).with_name("schema.sql")


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def _connect(db_path: str | Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db(db_path: str | Path) -> None:
    """Create all tables and indexes if they don't already exist."""
    sql = _SCHEMA.read_text(encoding="utf-8")
    with _connect(db_path) as con:
        con.executescript(sql)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def _rows_to_list(rows) -> list[dict]:
    return [dict(r) for r in rows]


def _bool(value: int | None) -> bool | None:
    if value is None:
        return None
    return bool(value)


# ---------------------------------------------------------------------------
# Farms
# ---------------------------------------------------------------------------

def create_farm(db_path: str | Path, farm_id: str, name: str,
                owner_name: str | None = None,
                village: str | None = None) -> dict:
    sql = """
        INSERT INTO farms (id, name, owner_name, village, created_at)
        VALUES (?, ?, ?, ?, ?)
    """
    with _connect(db_path) as con:
        con.execute(sql, (farm_id, name, owner_name, village, _now_utc()))
    return get_farm(db_path, farm_id)


def get_farm(db_path: str | Path, farm_id: str) -> dict | None:
    with _connect(db_path) as con:
        row = con.execute("SELECT * FROM farms WHERE id = ?", (farm_id,)).fetchone()
    if row is None:
        return None
    farm = dict(row)
    farm["aliases"] = _get_aliases(db_path, farm_id)
    return farm


def list_farms(db_path: str | Path) -> list[dict]:
    with _connect(db_path) as con:
        rows = con.execute("SELECT * FROM farms ORDER BY name").fetchall()
    farms = _rows_to_list(rows)
    for farm in farms:
        farm["aliases"] = _get_aliases(db_path, farm["id"])
    return farms


def _get_aliases(db_path: str | Path, farm_id: str) -> list[dict]:
    with _connect(db_path) as con:
        rows = con.execute(
            "SELECT * FROM farm_aliases WHERE farm_id = ? ORDER BY alias",
            (farm_id,),
        ).fetchall()
    return _rows_to_list(rows)


def add_farm_alias(db_path: str | Path, alias_id: str, farm_id: str,
                   alias: str, normalized_alias: str, confirmed: bool = False) -> dict:
    sql = """
        INSERT OR IGNORE INTO farm_aliases
            (id, farm_id, alias, normalized_alias, confirmed)
        VALUES (?, ?, ?, ?, ?)
    """
    with _connect(db_path) as con:
        con.execute(sql, (alias_id, farm_id, alias, normalized_alias, int(confirmed)))
        row = con.execute(
            "SELECT * FROM farm_aliases WHERE farm_id = ? AND normalized_alias = ?",
            (farm_id, normalized_alias),
        ).fetchone()
    return _row_to_dict(row)


def get_farm_aliases_by_normalized(db_path: str | Path,
                                   normalized: str) -> list[dict]:
    """Fast lookup via the idx_farm_aliases_normalized index."""
    with _connect(db_path) as con:
        rows = con.execute(
            "SELECT * FROM farm_aliases WHERE normalized_alias = ?", (normalized,)
        ).fetchall()
    return _rows_to_list(rows)


# ---------------------------------------------------------------------------
# Visits – core CRUD
# ---------------------------------------------------------------------------

def create_visit_raw(db_path: str | Path, visit_id: str, sequence: int,
                     raw_text: str, visit_date: str,
                     audio_path: str | None = None) -> dict:
    """
    Req 2: persist raw_text BEFORE parsing.  Returns the bare row dict.
    """
    sql = """
        INSERT INTO visits
            (id, sequence, raw_text, audio_path, visit_date, created_at,
             parse_status, match_status, farm_confirmed)
        VALUES (?, ?, ?, ?, ?, ?, 'pending', 'unmatched', 0)
    """
    with _connect(db_path) as con:
        con.execute(sql, (visit_id, sequence, raw_text,
                          audio_path, visit_date, _now_utc()))
    return _get_visit_row(db_path, visit_id)


def set_visit_parsed(db_path: str | Path, visit_id: str,
                     parsed: dict, match: dict) -> None:
    """Write parsed fields + match result after parsing succeeds."""
    ms = {
        "confident_match": "matched",
        "uncertain": "needs_confirmation",
        "no_match": "unmatched",
    }.get(match.get("status", "no_match"), "unmatched")

    sql = """
        UPDATE visits SET
            farm_id          = ?,
            plot             = ?,
            crop             = ?,
            problem          = ?,
            advice           = ?,
            follow_up        = ?,
            due_date         = ?,
            no_problem       = ?,
            match_status     = ?,
            parse_status     = 'parsed'
        WHERE id = ?
    """
    with _connect(db_path) as con:
        con.execute(sql, (
            match.get("farm_id"),
            parsed.get("plot"),
            parsed.get("crop"),
            parsed.get("problem"),
            parsed.get("advice"),
            parsed.get("follow_up"),
            parsed.get("due_date"),
            int(parsed["no_problem"]) if parsed.get("no_problem") is not None else None,
            ms,
            visit_id,
        ))
        # Upsert match candidates
        con.execute("DELETE FROM visit_match_candidates WHERE visit_id = ?", (visit_id,))
        for c in match.get("candidates", []):
            con.execute(
                "INSERT INTO visit_match_candidates (id, visit_id, farm_id, farm_name, score) VALUES (?, ?, ?, ?, ?)",
                (f"{visit_id}:{c['id']}", visit_id, c["id"], c["name"], c["score"]),
            )


def set_visit_parse_failed(db_path: str | Path, visit_id: str) -> None:
    with _connect(db_path) as con:
        con.execute(
            "UPDATE visits SET parse_status = 'failed' WHERE id = ?", (visit_id,)
        )


def set_visit_farm_confirmed(db_path: str | Path, visit_id: str,
                              farm_id: str | None,
                              snap_farm_name: str | None = None,
                              snap_owner_name: str | None = None,
                              snap_location: str | None = None) -> None:
    ms = "matched" if farm_id else "unmatched"
    sql = """
        UPDATE visits SET
            farm_id         = ?,
            farm_confirmed  = 1,
            match_status    = ?,
            snap_farm_name  = COALESCE(?, snap_farm_name),
            snap_owner_name = COALESCE(?, snap_owner_name),
            snap_location   = COALESCE(?, snap_location)
        WHERE id = ?
    """
    with _connect(db_path) as con:
        con.execute(sql, (farm_id, ms,
                          snap_farm_name, snap_owner_name, snap_location,
                          visit_id))


def update_visit_parsed_fields(db_path: str | Path, visit_id: str,
                                changes: dict, new_match: dict | None = None) -> None:
    """Apply a partial correction to parsed fields."""
    sets, params = [], []
    field_map = {
        "farmer":     "farmer_statement",
        "plot":       "plot",
        "crop":       "crop",
        "problem":    "problem",
        "advice":     "advice",
        "follow_up":  "follow_up",
        "due_date":   "due_date",
        "no_problem": "no_problem",
    }
    for key, col in field_map.items():
        if key in changes:
            val = changes[key]
            if key == "no_problem" and val is not None:
                val = int(val)
            sets.append(f"{col} = ?")
            params.append(val)
    if new_match:
        ms = {
            "confident_match": "matched",
            "uncertain": "needs_confirmation",
            "no_match": "unmatched",
        }.get(new_match.get("status", "no_match"), "unmatched")
        sets += ["farm_id = ?", "match_status = ?", "farm_confirmed = 0"]
        params += [new_match.get("farm_id"), ms]
    if not sets:
        return
    params.append(visit_id)
    with _connect(db_path) as con:
        con.execute(f"UPDATE visits SET {', '.join(sets)} WHERE id = ?", params)
        if new_match:
            con.execute("DELETE FROM visit_match_candidates WHERE visit_id = ?", (visit_id,))
            for c in new_match.get("candidates", []):
                con.execute(
                    "INSERT INTO visit_match_candidates (id, visit_id, farm_id, farm_name, score) VALUES (?, ?, ?, ?, ?)",
                    (f"{visit_id}:{c['id']}", visit_id, c["id"], c["name"], c["score"]),
                )


def set_completed_by(db_path: str | Path, visit_id: str,
                     completed_by_visit_id: str | None) -> None:
    with _connect(db_path) as con:
        con.execute(
            "UPDATE visits SET completed_by_visit_id = ? WHERE id = ?",
            (completed_by_visit_id, visit_id),
        )


def set_visit_snapshot(db_path: str | Path, visit_id: str,
                       snap_farm_name: str | None,
                       snap_owner_name: str | None,
                       snap_location: str | None) -> None:
    with _connect(db_path) as con:
        con.execute(
            """UPDATE visits SET
                snap_farm_name  = COALESCE(?, snap_farm_name),
                snap_owner_name = COALESCE(?, snap_owner_name),
                snap_location   = COALESCE(?, snap_location)
               WHERE id = ?""",
            (snap_farm_name, snap_owner_name, snap_location, visit_id),
        )


# ---------------------------------------------------------------------------
# Visits – read
# ---------------------------------------------------------------------------

def _get_visit_row(db_path: str | Path, visit_id: str) -> dict | None:
    with _connect(db_path) as con:
        row = con.execute("SELECT * FROM visits WHERE id = ?", (visit_id,)).fetchone()
        if row is None:
            return None
        visit = dict(row)
        cands = con.execute(
            "SELECT farm_id, farm_name, score FROM visit_match_candidates WHERE visit_id = ? ORDER BY score DESC",
            (visit_id,),
        ).fetchall()
    visit["_candidates"] = _rows_to_list(cands)
    return visit


def get_visit(db_path: str | Path, visit_id: str) -> dict | None:
    return _shape_visit(_get_visit_row(db_path, visit_id))


def list_visits_for_farm(db_path: str | Path, farm_id: str) -> list[dict]:
    with _connect(db_path) as con:
        rows = con.execute(
            "SELECT * FROM visits WHERE farm_id = ? ORDER BY visit_date DESC, sequence DESC",
            (farm_id,),
        ).fetchall()
    return [_shape_visit(dict(r)) for r in rows]


def get_next_sequence(db_path: str | Path) -> int:
    with _connect(db_path) as con:
        row = con.execute("SELECT COALESCE(MAX(sequence), 0) + 1 AS seq FROM visits").fetchone()
    return row["seq"]


def get_all_visits_for_reconcile(db_path: str | Path) -> list[dict]:
    """Return minimal dicts for follow-up reconciliation (sorted by date, sequence)."""
    with _connect(db_path) as con:
        rows = con.execute(
            "SELECT id, farm_id, visit_date, sequence, follow_up FROM visits ORDER BY visit_date, sequence"
        ).fetchall()
    return _rows_to_list(rows)


# ---------------------------------------------------------------------------
# Visits – shape into API-compatible dict
# ---------------------------------------------------------------------------

def _shape_visit(raw: dict | None) -> dict | None:
    if raw is None:
        return None
    cands = raw.pop("_candidates", [])
    # Reconstruct "parsed" sub-dict expected by existing API / frontend
    ms_map = {
        "matched": "confident_match",
        "needs_confirmation": "uncertain",
        "unmatched": "no_match",
    }
    parsed = {
        "farmer":     raw.get("farmer_statement"),
        "plot":       raw.get("plot"),
        "crop":       raw.get("crop"),
        "problem":    raw.get("problem"),
        "advice":     raw.get("advice"),
        "follow_up":  raw.get("follow_up"),
        "due_date":   raw.get("due_date"),
        "no_problem": _bool(raw.get("no_problem")),
    }
    farm_id = raw.get("farm_id")
    match_status_raw = raw.get("match_status", "unmatched")
    match_status_api = ms_map.get(match_status_raw, "no_match")
    match = {
        "status":     match_status_api,
        "farm_id":    farm_id if match_status_raw == "matched" else (farm_id if match_status_raw == "needs_confirmation" else None),
        "candidates": [{"id": c["farm_id"], "name": c["farm_name"], "score": c["score"]} for c in cands],
    }
    farm_info = {
        "farm_name":  raw.get("snap_farm_name"),
        "owner_name": raw.get("snap_owner_name"),
        "location":   raw.get("snap_location"),
    }
    return {
        "id":             raw["id"],
        "sequence":       raw["sequence"],
        "raw_text":       raw["raw_text"],
        "audio_path":     raw.get("audio_path"),
        "visit_date":     raw["visit_date"],
        "created_at":     raw["created_at"],
        "parse_status":   raw.get("parse_status", "pending"),
        "farm_id":        farm_id,
        "farm_confirmed": bool(raw.get("farm_confirmed", 0)),
        "match_status":   match_status_raw,     # DB form (matched/needs_confirmation/unmatched)
        "parsed":         parsed,
        "match":          match,                # API form for frontend
        "farm_info":      farm_info,
        "completed_by":   raw.get("completed_by_visit_id"),
    }


# ---------------------------------------------------------------------------
# Follow-ups  (Req 4)
# ---------------------------------------------------------------------------

def upsert_followup(db_path: str | Path, followup_id: str,
                    visit_id: str, farm_id: str | None,
                    promised_text: str, due_date: str | None,
                    status: str = "pending",
                    completed_by_visit_id: str | None = None) -> dict:
    sql = """
        INSERT INTO followups
            (id, visit_id, farm_id, promised_text, due_date, status, completed_by_visit_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            farm_id               = excluded.farm_id,
            promised_text         = excluded.promised_text,
            due_date              = excluded.due_date,
            status                = excluded.status,
            completed_by_visit_id = excluded.completed_by_visit_id
    """
    with _connect(db_path) as con:
        con.execute(sql, (followup_id, visit_id, farm_id,
                          promised_text, due_date, status, completed_by_visit_id))
        row = con.execute("SELECT * FROM followups WHERE id = ?", (followup_id,)).fetchone()
    return _row_to_dict(row)


def get_followup_by_visit(db_path: str | Path, visit_id: str) -> dict | None:
    with _connect(db_path) as con:
        row = con.execute(
            "SELECT * FROM followups WHERE visit_id = ?", (visit_id,)
        ).fetchone()
    return _row_to_dict(row)


def update_followup_status(db_path: str | Path, followup_id: str,
                            status: str,
                            completed_by_visit_id: str | None = None) -> None:
    with _connect(db_path) as con:
        con.execute(
            "UPDATE followups SET status = ?, completed_by_visit_id = ? WHERE id = ?",
            (status, completed_by_visit_id, followup_id),
        )


def list_open_followups(db_path: str | Path, as_of: str | None = None) -> dict:
    """
    Returns the same overdue / upcoming / undated / completed buckets
    the existing /followups endpoint returns, now driven from the DB.
    Uses the v_open_followups view for 'pending' and direct table for completed.
    """
    with _connect(db_path) as con:
        rows = con.execute(
            """
            SELECT fu.id, fu.visit_id, fu.farm_id, f.name AS farm_name,
                   fu.promised_text, fu.due_date, fu.status,
                   fu.completed_by_visit_id
            FROM followups fu
            LEFT JOIN farms f ON f.id = fu.farm_id
            ORDER BY fu.due_date NULLS LAST
            """
        ).fetchall()
    reference = as_of  # ISO date string or None
    result: dict[str, list] = {"overdue": [], "upcoming": [], "undated": [], "completed": []}
    for row in rows:
        item = {
            "note_id":      row["visit_id"],
            "farm_id":      row["farm_id"],
            "farm_name":    row["farm_name"],
            "follow_up":    row["promised_text"],
            "due_date":     row["due_date"],
            "completed_by": row["completed_by_visit_id"],
        }
        if item["completed_by"]:
            bucket = "completed"
        elif not item["due_date"]:
            bucket = "undated"
        elif reference and item["due_date"] < reference:
            bucket = "overdue"
        elif reference and item["due_date"] >= reference:
            bucket = "upcoming"
        else:
            bucket = "undated"
        result[bucket].append(item)
    for items in result.values():
        items.sort(key=lambda x: x["due_date"] or "9999")
    return result


# ---------------------------------------------------------------------------
# Reports (Req 5 & 6) – uses v_monthly_counts view
# ---------------------------------------------------------------------------

def monthly_report(db_path: str | Path, month: str) -> dict:
    """
    month: 'YYYY-MM'
    Uses v_monthly_counts view + direct queries for problems/advice lists.
    """
    with _connect(db_path) as con:
        summary = con.execute(
            "SELECT * FROM v_monthly_counts WHERE month = ?", (month,)
        ).fetchone()
        visits = con.execute(
            "SELECT * FROM visits WHERE substr(visit_date, 1, 7) = ? ORDER BY visit_date, sequence",
            (month,),
        ).fetchall()
    visit_list = [_shape_visit(dict(v)) for v in visits]
    problems = [
        {"note_id": v["id"], "text": v["parsed"]["problem"]}
        for v in visit_list
        if v["parsed"]["problem"] and not v["parsed"]["no_problem"]
    ]
    advice = [
        {"note_id": v["id"], "text": v["parsed"]["advice"]}
        for v in visit_list
        if v["parsed"]["advice"]
    ]
    s = dict(summary) if summary else {}
    return {
        "month":           month,
        "total_visits":    s.get("total_visits", 0),
        "unique_farms":    s.get("distinct_farms", 0),
        "unmatched_visits": s.get("unmatched_visits", 0),
        "no_problem_count": s.get("no_problem_visits", 0),
        "problems":        problems,
        "advice":          advice,
        "visits":          visit_list,
    }


# ---------------------------------------------------------------------------
# Farm history query (Req 5 & 6) – uses v_farm_history view
# ---------------------------------------------------------------------------

def farm_history(db_path: str | Path, farm_id: str) -> list[dict]:
    """All visits for a farm via the v_farm_history view, most recent first."""
    with _connect(db_path) as con:
        rows = con.execute(
            "SELECT id FROM v_farm_history WHERE farm_id = ?", (farm_id,)
        ).fetchall()
    visit_ids = [r["id"] for r in rows]
    return [v for vid in visit_ids if (v := get_visit(db_path, vid)) is not None]
