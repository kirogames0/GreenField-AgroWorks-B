"""
Read-only tools (Person B). These are always available regardless of
role -- they back `check_field_status` and `get_inventory`, and their
schemas are what tools/list returns for a field_hand session.

Each schema uses real JSON Schema constraints, `required`, and
`additionalProperties: false` per the grading rubric -- no bare
dicts or **kwargs tools.
"""

import sqlite3
from datetime import date


AUTHENTICATE_SCHEMA = {
    "name": "authenticate",
    "description": (
        "Authenticate a session with a worker_id. Updates the session's "
        "role based on the worker's certification status. If role changes, "
        "sends a notification and tool list is updated."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "worker_id": {
                "type": "string",
                "description": "Worker identifier, e.g. 'w1' or '1'.",
            }
        },
        "required": ["worker_id"],
        "additionalProperties": False,
    },
}

CHECK_FIELD_STATUS_SCHEMA = {
    "name": "check_field_status",
    "description": (
        "Look up the current crop stage, last chemical treatment, and "
        "next required action for a single field. Read-only -- does not "
        "modify any records."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "field_id": {
                "type": "string",
                "pattern": "^f[0-9]+$",
                "description": "Field identifier, e.g. 'f1'.",
            }
        },
        "required": ["field_id"],
        "additionalProperties": False,
    },
}

GET_INVENTORY_SCHEMA = {
    "name": "get_inventory",
    "description": (
        "Return current on-hand quantity for a chemical, or all "
        "chemicals in inventory if chemical_id is omitted. Read-only."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "chemical_id": {
                "type": "string",
                "pattern": "^chem[0-9]+$",
                "description": "Optional. Restrict to a single chemical, e.g. 'chem2'.",
            }
        },
        "required": [],
        "additionalProperties": False,
    },
}

GENERATE_COMPLIANCE_REPORT_SCHEMA = {
    "name": "generate_compliance_report",
    "description": (
        "Generate a chemical-application compliance report for a buyer "
        "across a date range. Long-running: reports progress per field "
        "processed via notifications/progress."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "buyer_id": {"type": "string", "description": "Buyer identifier."},
            "start_date": {
                "type": "string",
                "format": "date",
                "description": "ISO date, inclusive, e.g. '2026-01-01'.",
            },
            "end_date": {
                "type": "string",
                "format": "date",
                "description": "ISO date, inclusive, e.g. '2026-07-01'.",
            },
        },
        "required": ["buyer_id", "start_date", "end_date"],
        "additionalProperties": False,
    },
}

REQUEST_PESTICIDE_APPLICATION_SCHEMA = {
    "name": "request_pesticide_application",
    "description": (
        "Request to apply a chemical pesticide to a field. Requires "
        "certified applicator role. Creates a Chemical_Applications record "
        "with Pending status, awaiting approval from a certified approver."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "field_id": {
                "type": "string",
                "pattern": "^f[0-9]+$",
                "description": "Field to apply chemical to, e.g. 'f1'.",
            },
            "chemical_id": {
                "type": "string",
                "pattern": "^chem[0-9]+$",
                "description": "Chemical to apply, e.g. 'chem1'.",
            },
            "worker_id": {
                "type": "string",
                "description": "Worker requesting application (must be certified applicator).",
            },
        },
        "required": ["field_id", "chemical_id", "worker_id"],
        "additionalProperties": False,
    },
}

STORE_EPISODIC_MEMORY_SCHEMA = {
    "name": "store_episodic_memory",
    "description": (
        "Persist a short-lived episodic memory from the buffer overflow router."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {"type": "string"},
            "role": {"type": "string"},
            "content": {"type": "string"},
            "source": {"type": "string"},
            "created_at": {"type": "string", "format": "date"},
        },
        "required": ["session_id", "role", "content", "source"],
        "additionalProperties": False,
    },
}

FETCH_EPISODIC_MEMORY_SCHEMA = {
    "name": "fetch_episodic_memory",
    "description": (
        "Fetch recent episodic memory items for a session, optionally filtered by query terms."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {"type": "string"},
            "query": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
        },
        "required": ["session_id"],
        "additionalProperties": False,
    },
}


def store_episodic_memory(args: dict, cursor: sqlite3.Cursor) -> dict:
    session_id = args["session_id"]
    role = args.get("role", "any")
    content = args["content"]
    source = args["source"]
    created_at = args.get("created_at", date.today().isoformat())

    cursor.execute(
        "INSERT INTO EpisodicMemory (session_id, role, content, source, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, source, created_at),
    )
    cursor.connection.commit()

    return {
        "stored": True,
        "session_id": session_id,
        "source": source,
        "created_at": created_at,
    }


def fetch_episodic_memory(args: dict, cursor: sqlite3.Cursor) -> dict:
    session_id = args["session_id"]
    query = args.get("query", "").lower()
    limit = int(args.get("limit", 5))

    if query:
        query_pattern = f"%{query}%"
        cursor.execute(
            "SELECT content, source, created_at FROM EpisodicMemory WHERE session_id = ? AND lower(content) LIKE ? ORDER BY id DESC LIMIT ?",
            (session_id, query_pattern, limit),
        )
    else:
        cursor.execute(
            "SELECT content, source, created_at FROM EpisodicMemory WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        )

    rows = cursor.fetchall()
    memories = [
        {"content": row[0], "source": row[1], "created_at": row[2]} for row in rows
    ]

    return {
        "session_id": session_id,
        "memories": memories,
    }


def check_field_status(args: dict, cursor: sqlite3.Cursor) -> dict:
    """
    Look up field status by field_id (string format like 'f1').
    Returns field info including crop, crop stage, and last treatment.
    """
    field_id_str = args["field_id"]
    
    # Convert string ID (e.g., "f1") to integer (1)
    try:
        field_id = int(field_id_str[1:]) if field_id_str.startswith('f') else int(field_id_str)
    except (ValueError, IndexError):
        raise ValueError(f"Invalid field_id format: {field_id_str}")
    
    cursor.execute(
        """SELECT f.field_id, f.site_name, c.crop_name, c.growth_stage,
                  f.last_treatment_date, f.last_treatment_chemical_id
           FROM Fields f
           LEFT JOIN Crops c ON f.crop_id = c.crop_id
           WHERE f.field_id = ?""",
        (field_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"No such field: {field_id_str}")
    return {
        "field_id": f"f{row[0]}",
        "site_name": row[1],
        "crop": row[2],
        "crop_stage": row[3],
        "last_treatment_date": row[4],
        "last_treatment_chemical_id": row[5],
    }


def get_inventory(args: dict, cursor: sqlite3.Cursor) -> dict:
    """
    Look up inventory quantities for chemicals.
    Accepts optional chemical_id in format 'chem1'.
    """
    chemical_id_str = args.get("chemical_id")
    
    if chemical_id_str:
        # Convert string ID (e.g., "chem2") to integer (2)
        try:
            chemical_id = int(chemical_id_str.replace('chem', '')) if 'chem' in chemical_id_str else int(chemical_id_str)
        except ValueError:
            raise ValueError(f"Invalid chemical_id format: {chemical_id_str}")
        
        cursor.execute(
            "SELECT chemical_id, quantity_on_hand, unit FROM Inventory WHERE chemical_id = ?",
            (chemical_id,),
        )
        rows = cursor.fetchall()
    else:
        cursor.execute("SELECT chemical_id, quantity_on_hand, unit FROM Inventory")
        rows = cursor.fetchall()

    return {
        "inventory": [
            {"chemical_id": f"chem{r[0]}", "quantity_on_hand": r[1], "unit": r[2]} for r in rows
        ]
    }


def request_pesticide_application(args: dict, cursor: sqlite3.Cursor, worker_session_role: str) -> dict:
    """
    Request a pesticide application. Defensive write-tool: only certified applicators
    can make this request. Creates a Chemical_Applications record with Pending status.
    """
    # Verify worker has certified_applicator role
    if worker_session_role != "certified_applicator":
        raise ValueError(f"Only certified applicators can request pesticide applications. Current role: {worker_session_role}")
    
    field_id_str = args.get("field_id")
    chemical_id_str = args.get("chemical_id")
    worker_id_str = args.get("worker_id")
    
    if not all([field_id_str, chemical_id_str, worker_id_str]):
        raise ValueError("field_id, chemical_id, and worker_id are required")
    
    # Parse IDs
    try:
        field_id = int(field_id_str[1:]) if field_id_str.startswith('f') else int(field_id_str)
        chemical_id = int(chemical_id_str.replace('chem', '')) if 'chem' in chemical_id_str else int(chemical_id_str)
        worker_id = int(worker_id_str[1:]) if worker_id_str.startswith('w') else int(worker_id_str)
    except (ValueError, IndexError):
        raise ValueError(f"Invalid ID format(s): field_id={field_id_str}, chemical_id={chemical_id_str}, worker_id={worker_id_str}")
    
    # Verify field exists
    cursor.execute("SELECT field_id FROM Fields WHERE field_id = ?", (field_id,))
    if cursor.fetchone() is None:
        raise ValueError(f"No such field: {field_id_str}")
    
    # Verify chemical exists
    cursor.execute("SELECT chemical_id, is_restricted FROM Chemicals WHERE chemical_id = ?", (chemical_id,))
    chem_row = cursor.fetchone()
    if chem_row is None:
        raise ValueError(f"No such chemical: {chemical_id_str}")
    
    is_restricted = chem_row[1]
    
    # Verify worker exists and is certified
    cursor.execute("SELECT worker_id, is_certified FROM Workers WHERE worker_id = ?", (worker_id,))
    worker_row = cursor.fetchone()
    if worker_row is None:
        raise ValueError(f"No such worker: {worker_id_str}")
    if not worker_row[1]:
        raise ValueError(f"Worker {worker_id_str} is not certified to apply chemicals")
    
    # Create application record with Pending status
    from datetime import date
    today = str(date.today())
    
    cursor.execute(
        """INSERT INTO Chemical_Applications 
           (field_id, chemical_id, requested_by, status, request_date)
           VALUES (?, ?, ?, ?, ?)""",
        (field_id, chemical_id, worker_id, "Pending", today)
    )
    cursor.connection.commit()
    
    application_id = cursor.lastrowid
    
    return {
        "application_id": application_id,
        "field_id": field_id_str,
        "chemical_id": chemical_id_str,
        "worker_id": worker_id_str,
        "status": "Pending",
        "request_date": today,
        "is_restricted": bool(is_restricted),
        "message": f"Application {application_id} created with Pending status. Awaiting approval from certified approver."
    }
