"""
Demonstrates the difference between ungrounded LLM self-critique
and grounded database validation for Issue #13.
"""

import json
from planning.algorithms.environment import Environment


def simulate_ungrounded_llm_critique(state: str) -> tuple[float, str]:
    """
    Simulates an LLM evaluating its own output based purely on schema formatting.
    """
    if "worker_id" in state and "chemical_id" in state:
        return 1.0, "The proposed action is logically structured. Looks good to proceed."
    return 0.0, "Missing parameters."


def run_demonstration():
    print("--------------------------------------------------")
    print("GROUNDING DEMONSTRATION")
    print("--------------------------------------------------")

    # Deliberately broken plan: Uncertified worker assigned to restricted chemical
    bad_plan_state = json.dumps({
        "action_name": "request_pesticide_application",
        "worker_id": "w2",
        "chemical_id": "chem2",
        "field_id": "f1"
    })

    print("\n[Proposed Sub-Task State]")
    print(bad_plan_state)

    print("\n--- TEST 1: Ungrounded Self-Critique ---")
    ungrounded_score, ungrounded_feedback = simulate_ungrounded_llm_critique(bad_plan_state)
    print(f"Score   : {ungrounded_score}")
    print(f"Feedback: {ungrounded_feedback}")
    if ungrounded_score == 1.0:
        print("Result  : FAILED (Passed an invalid plan)")

    print("\n--- TEST 2: Grounded Database Environment ---")
    real_env = Environment()
    feedback = real_env.evaluate(state=bad_plan_state)
    print(f"Score   : {feedback.score}")
    print(f"Feedback: {feedback.details[0]}")
    if not feedback.success:
        print("Result  : SUCCESS (Rejected the invalid plan)")
    print("--------------------------------------------------\n")


if __name__ == "__main__":
    run_demonstration()