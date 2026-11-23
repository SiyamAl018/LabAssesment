"""FastAPI service – SQLite-backed, all requirements implemented.

Req 2  – raw_text written to DB *before* parsing (verbatim, never altered).
Req 3  – farms + farm_aliases tables; aliases indexed on normalized_alias.
Req 1&6 – parsed fields on visits; match_status ∈ {matched, needs_confirmation, unmatched}.
Req 4  – followups table synced on every write.
Req 5&6 – views v_farm_history, v_monthly_counts, v_open_followups; endpoint indexes.
"""
import logging
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from . import db as database
from .parsing import FIELDS, due_date, match_farm, normalize_name, parse_note

logger = logging.getLogger(__name__)


def today() -> date:
    return datetime.now(timezone(timedelta(hours=6))).date()


# ---------------------------------------------------------------------------
# Pydantic models  (unchanged surface area – frontend compatibility)
# ---------------------------------------------------------------------------

class FarmInfo(BaseModel):
    owner_name: str | None = None
    farm_name:  str | None = None
    location:   str | None = None
    plot:       str | None = None
    crop:       str | None = None


class NoteInput(BaseModel):
    raw_text:   str      = ""
    visit_date: date     = Field(default_factory=today)
    farm_id:    str | None = None
    farm_info:  FarmInfo = Field(default_factory=FarmInfo)
    audio_path: str | None = None          # Req 2: optional audio


class Correction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    farmer:     str | None  = None
    plot:       str | None  = None
    crop:       str | None  = None
    problem:    str | None  = None
    advice:     str | None  = None
    follow_up:  str | None  = None
    due_date:   date | None = None
    no_problem: bool | None = None


class FarmInput(BaseModel):
    name:       str            = Field(min_length=1)
    owner_name: str | None     = None
    location:   str | None     = None      # maps to village in DB


class FarmConfirmation(BaseModel):
    farm_id: str | None = None
    alias:   str | None = None


# ---------------------------------------------------------------------------
# follow-up sync helper
# ---------------------------------------------------------------------------

def _sync_followup(db_path: str | Path, visit: dict) -> None:
    """Create or update a followup row whenever a visit has a follow_up phrase."""
    fu_text = visit["parsed"].get("follow_up")
    existing = database.get_followup_by_visit(db_path, visit["id"])
    if not fu_text:
        # No follow-up phrase → nothing to do (we keep existing rows intact)
        return
    followup_id = existing["id"] if existing else str(uuid4())
    completed_by = visit.get("completed_by")
    status = "completed" if completed_by else "pending"
    database.upsert_followup(
        db_path,
        followup_id=followup_id,
        visit_id=visit["id"],
        farm_id=visit.get("farm_id"),
        promised_text=fu_text,
        due_date=visit["parsed"].get("due_date"),
        status=status,
        completed_by_visit_id=completed_by,
    )


# ---------------------------------------------------------------------------
# Reconcile completed_by links (same logic as before, now against DB)
# ---------------------------------------------------------------------------

def reconcile(db_path: str | Path) -> None:
    """Rebuild completed_by_visit_id for all notes that have a follow_up."""
    all_visits = database.get_all_visits_for_reconcile(db_path)
    # sort by (visit_date, sequence) ascending
    all_visits.sort(key=lambda n: (n["visit_date"], n["sequence"]))
    for idx, note in enumerate(all_visits):
        if not note.get("follow_up") or not note.get("farm_id"):
            database.set_completed_by(db_path, note["id"], None)
            continue
        next_visit = next(
            (n for n in all_visits[idx + 1:]
             if note["farm_id"] and n.get("farm_id") == note["farm_id"]),
            None,
        )
        database.set_completed_by(db_path, note["id"],
                                  next_visit["id"] if next_visit else None)
    # Re-sync followup table statuses
    for note in all_visits:
        full = database.get_visit(db_path, note["id"])
        if full:
            _sync_followup(db_path, full)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(db_path=None):
    app = FastAPI(title="Farm visit notes", version="2.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(","),
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type"],
    )

    _db_path: Path = Path(
        db_path
        or os.environ.get("DB_PATH", str(Path(__file__).parent / "data" / "visits.db"))
    )
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    database.init_db(_db_path)
    app.state.db_path = _db_path

    router = APIRouter()

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @router.get("/health")
    def health():
        return {"status": "ok", "storage": "sqlite"}

    # ------------------------------------------------------------------
    # Notes / Visits
    # ------------------------------------------------------------------

    @router.post("/notes", status_code=201)
    def create_note(body: NoteInput):
        visit_id  = str(uuid4())
        seq       = database.get_next_sequence(_db_path)
        visit_date_str = body.visit_date.isoformat()

        # Req 2: persist raw text first, durably, before any parsing
        database.create_visit_raw(
            _db_path, visit_id, seq,
            body.raw_text, visit_date_str,
            audio_path=body.audio_path,
        )

        # Parse
        try:
            parsed = parse_note(body.raw_text, visit_date_str)
            # Merge explicit form fields
            for field, value in {
                "farmer": body.farm_info.owner_name,
                "plot":   body.farm_info.plot,
                "crop":   body.farm_info.crop,
            }.items():
                if value:
                    parsed[field] = value

            match = match_farm(
                body.farm_info.farm_name or parsed.get("farmer"),
                database.list_farms(_db_path),
            )
            database.set_visit_parsed(_db_path, visit_id, parsed, match)
        except Exception:
            logger.exception("Parsing failed for visit %s", visit_id)
            database.set_visit_parse_failed(_db_path, visit_id)
            parsed = {f: None for f in FIELDS}
            parsed.update({"no_problem": None, "due_date": None})
            match  = {"status": "no_match", "farm_id": None, "candidates": []}

        # Explicit farm selection overrides parsing
        selected = None
        if body.farm_id:
            selected = database.get_farm(_db_path, body.farm_id)
        if selected:
            database.set_visit_farm_confirmed(
                _db_path, visit_id, selected["id"],
                snap_farm_name  = selected.get("name"),
                snap_owner_name = selected.get("owner_name"),
                snap_location   = selected.get("village"),
            )
        else:
            # Save snapshot from form even when unconfirmed
            database.set_visit_snapshot(
                _db_path, visit_id,
                snap_farm_name  = body.farm_info.farm_name,
                snap_owner_name = body.farm_info.owner_name,
                snap_location   = body.farm_info.location,
            )

        reconcile(_db_path)
        visit = database.get_visit(_db_path, visit_id)
        if visit is None:
            raise HTTPException(500, "Visit could not be retrieved after save")
        return visit

    @router.get("/notes/{note_id}")
    def get_note(note_id: str):
        visit = database.get_visit(_db_path, note_id)
        if visit is None:
            raise HTTPException(404, "Note not found")
        return visit

    @router.patch("/notes/{note_id}")
    def correct_note(note_id: str, body: Correction):
        visit = database.get_visit(_db_path, note_id)
        if visit is None:
            raise HTTPException(404, "Note not found")

        changes = body.model_dump(exclude_unset=True, mode="json")

        # Infer due_date when follow_up changes but due_date was not given
        if "follow_up" in changes and "due_date" not in changes:
            changes["due_date"] = due_date(changes["follow_up"], visit["visit_date"])

        # Invalidate no_problem when problem is corrected
        if "problem" in changes and "no_problem" not in changes:
            changes["no_problem"] = None

        new_match = None
        if "farmer" in changes:
            new_match = match_farm(changes["farmer"], database.list_farms(_db_path))

        database.update_visit_parsed_fields(_db_path, note_id, changes, new_match)
        reconcile(_db_path)
        visit = database.get_visit(_db_path, note_id)
        if visit is None:
            raise HTTPException(404, "Note not found")
        return visit

    @router.post("/notes/{note_id}/confirm-farm")
    def confirm_farm(note_id: str, body: FarmConfirmation):
        visit = database.get_visit(_db_path, note_id)
        if visit is None:
            raise HTTPException(404, "Note not found")

        if body.farm_id:
            farm = database.get_farm(_db_path, body.farm_id)
            if farm is None:
                raise HTTPException(404, "Farm not found")
            # Learn alias (Req 3)
            alias_text = (
                body.alias
                or visit["farm_info"].get("farm_name")
                or visit["parsed"].get("farmer")
            )
            if alias_text:
                normalized = normalize_name(alias_text)
                if normalized:
                    existing = database.get_farm_aliases_by_normalized(_db_path, normalized)
                    already  = any(a["farm_id"] == body.farm_id for a in existing)
                    if not already:
                        database.add_farm_alias(
                            _db_path, str(uuid4()),
                            body.farm_id, alias_text, normalized, confirmed=True,
                        )
            database.set_visit_farm_confirmed(
                _db_path, note_id, body.farm_id,
                snap_farm_name  = farm.get("name"),
                snap_owner_name = farm.get("owner_name"),
                snap_location   = farm.get("village"),
            )
        else:
            database.set_visit_farm_confirmed(_db_path, note_id, None)

        reconcile(_db_path)
        visit = database.get_visit(_db_path, note_id)
        if visit is None:
            raise HTTPException(404, "Note not found")
        return visit

    # ------------------------------------------------------------------
    # Farms
    # ------------------------------------------------------------------

    @router.get("/farms")
    def farms():
        return database.list_farms(_db_path)

    @router.post("/farms", status_code=201)
    def create_farm(body: FarmInput):
        if not body.name.strip():
            raise HTTPException(422, "Farm name cannot be blank")
        farm = database.create_farm(
            _db_path, str(uuid4()), body.name,
            owner_name=body.owner_name,
            village=body.location,
        )
        return farm

    @router.get("/farms/{farm_id}/history")
    def farm_history(farm_id: str):
        farm = database.get_farm(_db_path, farm_id)
        if farm is None:
            raise HTTPException(404, "Farm not found")
        return database.farm_history(_db_path, farm_id)

    @router.get("/farms/{farm_id}/last-visit")
    def last_visit(farm_id: str):
        farm = database.get_farm(_db_path, farm_id)
        if farm is None:
            raise HTTPException(404, "Farm not found")
        history = database.farm_history(_db_path, farm_id)
        return history[0] if history else None

    # ------------------------------------------------------------------
    # Follow-ups  (Req 4)
    # ------------------------------------------------------------------

    @router.get("/followups")
    def followups(as_of: date | None = None):
        reference = (as_of or today()).isoformat()
        return database.list_open_followups(_db_path, as_of=reference)

    # ------------------------------------------------------------------
    # Reports  (Req 5 & 6)
    # ------------------------------------------------------------------

    @router.get("/reports")
    def report(month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")):
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month) or month.startswith("0000"):
            raise HTTPException(422, "Use a valid YYYY-MM month")
        return database.monthly_report(_db_path, month)

    app.include_router(router)
    app.include_router(router, prefix="/api", include_in_schema=False)
    return app


app = create_app()
