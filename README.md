# FarmLog

FastAPI backend and React frontend for farm visits. No database integration: records are stored in an atomic JSON file at `backend/data/notes.json` (gitignored). Run one backend worker/process only; file storage is intended for local development.

## Run (PowerShell from project root)

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt
.venv/Scripts/python -m uvicorn backend.main:app --reload --port 8000
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173. API documentation: http://localhost:8000/docs.
`VITE_API_BASE_URL` defaults to `http://localhost:8000/api`. Backend routes support both `/api` and unprefixed paths. `NOTES_FILE` overrides the storage file. `CORS_ORIGINS` accepts comma-separated frontend origins.

## Features and contracts

- `POST /notes`: accepts `raw_text` (including empty text), optional `visit_date` (YYYY-MM-DD), `farm_id`, and `farm_info` with owner_name, farm_name, location, plot, crop. Saves raw text before parsing. Unknown fields remain null; parsing failure returns a saved note with `parse_status: failed`.
- Every frontend visit collects an owner and farm name; selecting an existing farm fills its details. Each visit stores its own farm information snapshot. The API permits incomplete notes to preserve intake.
- `GET /notes/{id}` and `PATCH /notes/{id}`: retrieve notes and correct parsed fields only. Raw text and visit snapshots cannot be overwritten. Correction fields: farmer, plot, crop, problem, advice, follow_up, due_date, no_problem.
- `GET /farms`, `POST /farms`: list/register farms with name, owner_name, location. Farm IDs distinguish farms sharing a name or owner.
- `POST /notes/{id}/confirm-farm`: accepts farm_id (null means no match), optional alias. Saves the decision and alias. For a new farm, register it then confirm it.
- Matching normalizes case, punctuation, mia/miah/bhai and selected spelling variants, then uses RapidFuzz against farm names, owners and aliases. Scores >=90 with a >=10-point lead are confident; scores >=65 otherwise yield uncertain candidates; lower scores yield no match. Shared owner/name matches remain uncertain.
- `GET /followups`: overdue, upcoming (including today), undated and completed buckets. Optional `as_of=YYYY-MM-DD`. Relative dates use visit_date, never parsing time. A chronologically later visit to the same farm completes prior follow-ups; same-day visits use intake order. Backdated entries and farm reassignment reconcile completion links.
- `GET /farms/{id}/history`, `GET /farms/{id}/last-visit`: stored visits ordered by visit date and intake order. Last visit is null if no visits exist.
- `GET /reports?month=YYYY-MM`: stored totals, unique matched farms, unmatched visits, explicit no-problem count, problems, advice and all visits. Empty notes count as visits but are not guessed to be no-problem visits. Explicit no-problem visits count even without problem/advice content. Reports never invoke parsing or generation.

Parsing uses conservative English natural-speech rules and English/Bangla labeled fields. Example: `Farmer: Rahim Mia; Plot: north; Crop: rice; Problem: leaf spots; Advice: reduce watering; Follow-up: in two weeks`. Unsupported phrasing remains available in the raw transcript for manual field correction. Dates that cannot be determined remain undated.

## Checks

```powershell
.venv/Scripts/python -m pytest backend -q
cd frontend
npm run build
```
