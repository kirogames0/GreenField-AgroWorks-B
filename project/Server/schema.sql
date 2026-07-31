-- MINIMAL STOPGAP SCHEMA (Person B) -- Person A owns the real db/ folder.
-- This exists only so mcp_server tools have something to query while
-- the full schema/ERD/seed data is being built out.

CREATE TABLE IF NOT EXISTS workers (
    worker_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('field_hand', 'certified_applicator', 'manager')),
    certification_id TEXT
);

CREATE TABLE IF NOT EXISTS fields (
    field_id TEXT PRIMARY KEY,
    site_name TEXT NOT NULL,
    crop TEXT NOT NULL,
    crop_stage TEXT NOT NULL,
    last_treatment_date TEXT,
    last_treatment_chemical_id TEXT
);

CREATE TABLE IF NOT EXISTS chemicals (
    chemical_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    is_restricted_use INTEGER NOT NULL DEFAULT 0,  -- 1 = RUP, requires elicitation
    rei_hours INTEGER NOT NULL DEFAULT 0            -- re-entry interval
);

CREATE TABLE IF NOT EXISTS inventory (
    chemical_id TEXT PRIMARY KEY,
    quantity_on_hand REAL NOT NULL,
    unit TEXT NOT NULL,
    FOREIGN KEY (chemical_id) REFERENCES chemicals(chemical_id)
);

CREATE TABLE IF NOT EXISTS applications (
    application_id TEXT PRIMARY KEY,
    field_id TEXT NOT NULL,
    chemical_id TEXT NOT NULL,
    applicator_worker_id TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    buyer_id TEXT,
    FOREIGN KEY (field_id) REFERENCES fields(field_id),
    FOREIGN KEY (chemical_id) REFERENCES chemicals(chemical_id),
    FOREIGN KEY (applicator_worker_id) REFERENCES workers(worker_id)
);

-- Seed data: enough to demo read-only tools + one RUP case + one non-RUP case
INSERT OR IGNORE INTO workers VALUES
    ('w1', 'Dana Ruiz', 'field_hand', NULL),
    ('w2', 'Marcus Webb', 'certified_applicator', 'CERT-4821'),
    ('w3', 'Priya Anand', 'manager', NULL);

INSERT OR IGNORE INTO fields VALUES
    ('f1', 'North Ridge Site', 'strawberries', 'flowering', '2026-07-01', 'chem2'),
    ('f2', 'South Valley Site', 'lettuce', 'seedling', NULL, NULL);

INSERT OR IGNORE INTO chemicals VALUES
    ('chem1', 'General Fertilizer 10-10-10', 0, 0),
    ('chem2', 'Chlorpyrifos-based RUP', 1, 24);

INSERT OR IGNORE INTO inventory VALUES
    ('chem1', 400.0, 'lbs'),
    ('chem2', 15.0, 'gal');
