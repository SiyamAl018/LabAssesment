-- =============================================================
-- Farm Visit Notes – SQLite Schema
-- =============================================================
-- Req 2: Verbatim storage
-- Req 3: Farm identity
-- Req 1 & 6: Parsed fields + match_status
-- Req 4: Follow-ups
-- Req 5 & 6: Indexes + views
-- =============================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ----- Req 3: Farm identity ---------------------------------
CREATE TABLE IF NOT EXISTS farms (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,          -- canonical name
    owner_name      TEXT,
    village         TEXT,                   -- "village or notes" per req
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS farm_aliases (
    id               TEXT PRIMARY KEY,
    farm_id          TEXT NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    alias            TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    confirmed        INTEGER NOT NULL DEFAULT 0 CHECK (confirmed IN (0, 1))
);

-- Req 3: fast lookup on normalized alias
CREATE INDEX IF NOT EXISTS idx_farm_aliases_normalized
    ON farm_aliases (normalized_alias);

-- ----- Req 2: Verbatim storage ------------------------------
CREATE TABLE IF NOT EXISTS visits (
    id              TEXT PRIMARY KEY,
    sequence        INTEGER NOT NULL,
    raw_text        TEXT NOT NULL,          -- NEVER altered after first write
    audio_path      TEXT,                   -- optional audio recording path
    visit_date      TEXT NOT NULL,          -- ISO-8601 date YYYY-MM-DD
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),

    -- Req 1 & 6: Parsed fields (all nullable)
    farm_id         TEXT REFERENCES farms(id) ON DELETE SET NULL,
    plot            TEXT,
    crop            TEXT,
    problem         TEXT,
    farmer_statement TEXT,                  -- raw farmer quote / "advice" text
    advice          TEXT,
    follow_up       TEXT,
    due_date        TEXT,                   -- ISO-8601 date, nullable
    no_problem      INTEGER CHECK (no_problem IN (0, 1)),   -- boolean
    parse_status    TEXT NOT NULL DEFAULT 'pending'
                        CHECK (parse_status IN ('pending', 'parsed', 'failed')),

    -- Req 1 & 6: match status
    match_status    TEXT NOT NULL DEFAULT 'unmatched'
                        CHECK (match_status IN ('matched', 'needs_confirmation', 'unmatched')),
    farm_confirmed  INTEGER NOT NULL DEFAULT 0 CHECK (farm_confirmed IN (0, 1)),

    -- follow-up completion link
    completed_by_visit_id TEXT REFERENCES visits(id) ON DELETE SET NULL,

    -- snapshot of farm info at the time of the visit (denormalised, for history)
    snap_farm_name  TEXT,
    snap_owner_name TEXT,
    snap_location   TEXT
);

-- Req 5 & 6: indexes on visits
CREATE INDEX IF NOT EXISTS idx_visits_farm_date
    ON visits (farm_id, visit_date);

CREATE INDEX IF NOT EXISTS idx_visits_visit_date
    ON visits (visit_date);

-- match_candidates JSON blob stored separately (lightweight)
CREATE TABLE IF NOT EXISTS visit_match_candidates (
    id          TEXT PRIMARY KEY,
    visit_id    TEXT NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
    farm_id     TEXT NOT NULL,
    farm_name   TEXT NOT NULL,
    score       REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_match_candidates_visit
    ON visit_match_candidates (visit_id);

-- ----- Req 4: Follow-ups ------------------------------------
CREATE TABLE IF NOT EXISTS followups (
    id                   TEXT PRIMARY KEY,
    visit_id             TEXT NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
    farm_id              TEXT REFERENCES farms(id) ON DELETE SET NULL,
    promised_text        TEXT NOT NULL,
    due_date             TEXT,              -- ISO-8601 date, nullable
    status               TEXT NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending', 'completed', 'missed')),
    completed_by_visit_id TEXT REFERENCES visits(id) ON DELETE SET NULL
);

-- Req 5 & 6: indexes on followups
CREATE INDEX IF NOT EXISTS idx_followups_status_due
    ON followups (status, due_date);

CREATE INDEX IF NOT EXISTS idx_followups_visit
    ON followups (visit_id);

-- =============================================================
-- Req 5 & 6: Ready-made views
-- =============================================================

-- View: full farm history (all visits for a farm, most recent first)
CREATE VIEW IF NOT EXISTS v_farm_history AS
SELECT
    v.id,
    v.visit_date,
    v.created_at,
    v.farm_id,
    f.name            AS farm_name,
    f.village         AS farm_village,
    v.plot,
    v.crop,
    v.problem,
    v.advice,
    v.follow_up,
    v.due_date,
    v.no_problem,
    v.match_status,
    v.parse_status,
    v.raw_text
FROM visits v
LEFT JOIN farms f ON f.id = v.farm_id
ORDER BY v.visit_date DESC, v.sequence DESC;

-- View: monthly summary counts
-- Usage: SELECT * FROM v_monthly_counts WHERE month = '2026-11';
CREATE VIEW IF NOT EXISTS v_monthly_counts AS
SELECT
    substr(visit_date, 1, 7)               AS month,
    COUNT(*)                               AS total_visits,
    COUNT(DISTINCT farm_id)                AS distinct_farms,
    SUM(CASE WHEN no_problem = 1 THEN 1 ELSE 0 END)
                                           AS no_problem_visits,
    SUM(CASE WHEN farm_id IS NULL THEN 1 ELSE 0 END)
                                           AS unmatched_visits
FROM visits
GROUP BY substr(visit_date, 1, 7);

-- View: open follow-ups (pending, with farm info)
CREATE VIEW IF NOT EXISTS v_open_followups AS
SELECT
    fu.id              AS followup_id,
    fu.visit_id,
    fu.farm_id,
    f.name             AS farm_name,
    fu.promised_text,
    fu.due_date,
    fu.status,
    fu.completed_by_visit_id
FROM followups fu
LEFT JOIN farms f ON f.id = fu.farm_id
WHERE fu.status = 'pending'
ORDER BY fu.due_date NULLS LAST;
