CREATE TABLE Farms (
    farm_id INTEGER PRIMARY KEY,
    farm_name TEXT NOT NULL,
    location TEXT NOT NULL
);

CREATE TABLE Crops (
    crop_id INTEGER PRIMARY KEY,
    crop_name TEXT NOT NULL,
    growth_stage TEXT NOT NULL
);

CREATE TABLE Fields (
    field_id INTEGER PRIMARY KEY,
    farm_id INTEGER NOT NULL,
    crop_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    site_name TEXT NOT NULL,
    size_acres REAL NOT NULL CHECK(size_acres > 0),
    last_treatment_date TEXT,
    last_treatment_chemical_id INTEGER,
    FOREIGN KEY (farm_id) REFERENCES Farms(farm_id),
    FOREIGN KEY (crop_id) REFERENCES Crops(crop_id),
    FOREIGN KEY (last_treatment_chemical_id) REFERENCES Chemicals(chemical_id)
);

CREATE TABLE Chemicals (
    chemical_id INTEGER PRIMARY KEY,
    chemical_name TEXT NOT NULL,
    chemical_type TEXT NOT NULL,
    is_restricted BOOLEAN NOT NULL,
    reentry_hours INTEGER NOT NULL CHECK(reentry_hours >= 0),
    stock_quantity INTEGER NOT NULL CHECK(stock_quantity >= 0)
);

CREATE TABLE Workers (
    worker_id INTEGER PRIMARY KEY,
    worker_name TEXT NOT NULL,
    role TEXT NOT NULL,
    is_certified BOOLEAN NOT NULL
);

CREATE TABLE Chemical_Applications (
    application_id INTEGER PRIMARY KEY,
    field_id INTEGER NOT NULL,
    chemical_id INTEGER NOT NULL,
    requested_by INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('Pending','Approved','Rejected','Completed')
    ),
    request_date DATE NOT NULL,
    FOREIGN KEY (field_id) REFERENCES Fields(field_id),
    FOREIGN KEY (chemical_id) REFERENCES Chemicals(chemical_id),
    FOREIGN KEY (requested_by) REFERENCES Workers(worker_id)
);

CREATE TABLE Approvals (
    approval_id INTEGER PRIMARY KEY,
    application_id INTEGER UNIQUE,
    approved_by INTEGER NOT NULL,
    decision TEXT NOT NULL CHECK (
        decision IN ('Approved','Rejected')
    ),
    approval_date DATE,
    FOREIGN KEY (application_id) REFERENCES Chemical_Applications(application_id),
    FOREIGN KEY (approved_by) REFERENCES Workers(worker_id)
);

CREATE TABLE Safety_Policies (
    policy_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE Inventory (
    inventory_id INTEGER PRIMARY KEY,
    chemical_id INTEGER NOT NULL UNIQUE,
    quantity_on_hand INTEGER NOT NULL CHECK(quantity_on_hand >= 0),
    unit TEXT NOT NULL,
    FOREIGN KEY (chemical_id) REFERENCES Chemicals(chemical_id)
);

CREATE TABLE EpisodicMemory (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);