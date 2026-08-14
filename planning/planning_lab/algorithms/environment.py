import sqlite3
import os
import json
import re
from ..models import EnvironmentFeedback


DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "greenfield.db"
)


class Environment:
    """Evaluates proposed plans against GreenField database constraints."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def evaluate(self, state: str) -> EnvironmentFeedback:
        """
        Validates the LLM's proposed action against real database records.
        """
        worker_id = None
        chemical_id = None

        try:
            data = json.loads(state)
            worker_id = data.get("worker_id")
            chemical_id = data.get("chemical_id")
        except json.JSONDecodeError:
            worker_match = re.search(r'worker_id["\s:]+([a-zA-Z0-9_]+)', state, re.IGNORECASE)
            chem_match = re.search(r'chemical_id["\s:]+([a-zA-Z0-9_]+)', state, re.IGNORECASE)
            if worker_match:
                worker_id = worker_match.group(1)
            if chem_match:
                chemical_id = chem_match.group(1)

        if not worker_id or not chemical_id:
            return EnvironmentFeedback(
                success=True,
                score=0.8,
                details=["No explicit pesticide application parameters detected."]
            )

        try:
            w_id_int = int(str(worker_id).replace('w', ''))
            c_id_int = int(str(chemical_id).replace('chem', ''))
        except ValueError:
            return EnvironmentFeedback(
                success=False,
                score=0.0,
                details=["Formatting error: IDs must be numeric or standard format."]
            )

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT chemical_name, is_restricted FROM Chemicals WHERE chemical_id = ?", (c_id_int,))
            chem_data = cursor.fetchone()

            if not chem_data:
                return EnvironmentFeedback(
                    success=False,
                    score=0.0,
                    details=[f"Inventory Error: Chemical {chemical_id} not found."]
                )

            chem_name, is_restricted = chem_data

            if is_restricted:
                cursor.execute("SELECT worker_name, is_certified FROM Workers WHERE worker_id = ?", (w_id_int,))
                worker_data = cursor.fetchone()

                if not worker_data:
                    return EnvironmentFeedback(
                        success=False,
                        score=0.0,
                        details=[f"HR Error: Worker {worker_id} not found."]
                    )

                worker_name, is_certified = worker_data

                if not is_certified:
                    return EnvironmentFeedback(
                        success=False,
                        score=0.0,
                        details=[
                            f"Compliance Violation: Worker '{worker_name}' is not certified to apply '{chem_name}'."]
                    )

            return EnvironmentFeedback(
                success=True,
                score=1.0,
                details=["Application plan passes compliance and inventory checks."]
            )

        except sqlite3.Error as e:
            return EnvironmentFeedback(
                success=False,
                score=0.0,
                details=[f"Database error: {str(e)}"]
            )
        finally:
            if 'conn' in locals():
                conn.close()