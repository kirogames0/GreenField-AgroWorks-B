"""
Run this locally (needs a real MISTRAL_API_KEY in .env) to confirm
routing.py actually drives PS/ToT/LATS end-to-end before the demo.
Not part of the graded deliverable -- just a fast sanity check.

Usage: python planning/smoke_test_routing.py
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from config import get_llm_client
from routing import run_routed_subtask

llm = get_llm_client()

print("--- t1 (plan_and_solve) ---")
r1 = run_routed_subtask("t1", "Check field status for f1", llm)
print(r1["method"], "| llm_calls:", r1["llm_calls"])
print(r1["result"][:200], "...\n")

print("--- t2 (tree_of_thoughts) ---")
r2 = run_routed_subtask("t2", "Determine optimal timing for pesticide application", llm, tot_depth=1, tot_beam_width=2)
print(r2["method"], "| llm_calls (approx):", r2["llm_calls"])
print(r2["result"][:200], "...\n")

print("--- t5 (lats, toolkit's default randomized environment for this smoke test) ---")
r5 = run_routed_subtask("t5", "Submit pesticide request to apply chem2 to f1", llm, lats_iterations=1, lats_n_actions=2)
print(r5["method"], "| success:", r5["success"], "| best_score:", r5["best_score"])
print(r5["result"][:200], "...\n")

print("All three methods ran without exception.")
