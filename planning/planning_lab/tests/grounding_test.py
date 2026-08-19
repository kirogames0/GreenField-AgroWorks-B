"""
Demonstrates the difference between ungrounded LLM self-critique
and grounded database validation for Issue #13.
"""
import json
from planning.planning_lab.algorithms.environment import Environment


def call_llm(prompt: str) -> str:
    """
    Calls the LLM using centralized config.
    Returns the LLM's raw response.
    """
    from config import get_llm_client
    llm = get_llm_client()
    response = llm.invoke(prompt)
    return response.content


def ungrounded_llm_critique(state: str) -> tuple[float, str]:
    """
    Uses the LLM to evaluate a proposed action based purely on schema/formatting.
    Ungrounded: No database or environment constraints are checked.
    """
    critique_prompt = f"""
    You are an AI assistant evaluating a proposed agricultural task.
    The task must include 'worker_id', 'chemical_id', and 'field_id'.
    Do NOT check if the worker/chemical/field actually exists in the database.
    
    Proposed task: {state}
    
    Respond with:
    - A score from 0.0 to 1.0 (1.0 = valid structure, 0.0 = invalid).
    - A one-sentence justification.
    
    Format your response as: SCORE|JUSTIFICATION
    Example: 1.0|The proposed action is logically structured.
    """
    llm_response = call_llm(critique_prompt)
    try:
        score_str, feedback = llm_response.split("|", 1)
        return float(score_str.strip()), feedback.strip()
    except Exception:
        return 0.0, "LLM response format error."


def run_demonstration():
    print("--------------------------------------------------")
    print("GROUNDING DEMONSTRATION")
    print("--------------------------------------------------")

    # Deliberately broken plan: Uncertified worker assigned to restricted chemical
    bad_plan_state = json.dumps({
        "action_name": "request_pesticide_application",
        "worker_id": "w2",  # Uncertified for chem2
        "chemical_id": "chem2",  # Restricted chemical
        "field_id": "f1"
    })

    print("\n[Proposed Sub-Task State]")
    print(bad_plan_state)

    print("\n--- TEST 1: Ungrounded LLM Critique ---")
    ungrounded_score, ungrounded_feedback = ungrounded_llm_critique(bad_plan_state)
    print(f"Score   : {ungrounded_score}")
    print(f"Feedback: {ungrounded_feedback}")
    if ungrounded_score == 1.0:
        print("Result  : FAILED (Ungrounded LLM passed an invalid plan)")

    print("\n--- TEST 2: Grounded Database Environment ---")
    real_env = Environment()
    feedback = real_env.evaluate(state=bad_plan_state)
    print(f"Score   : {feedback.score}")
    print(f"Feedback: {feedback.details[0]}")
    if not feedback.success:
        print("Result  : SUCCESS (Grounded environment rejected the invalid plan)")
    
    # Test case: Non-existent chemical (ungrounded LLM will pass, grounded will fail)
    nonexistent_plan = json.dumps({
        "action_name": "request_pesticide_application",
        "worker_id": "w1",
        "chemical_id": "nonexistent_chem",
        "field_id": "f1"
    })
    print("\n[Proposed Sub-Task State (Non-existent Chemical)]")
    print(nonexistent_plan)
    
    print("\n--- TEST 3: Ungrounded LLM (Non-existent Chemical) ---")
    ungrounded_score, ungrounded_feedback = ungrounded_llm_critique(nonexistent_plan)
    print(f"Score   : {ungrounded_score}")
    print(f"Feedback: {ungrounded_feedback}")
    if ungrounded_score == 1.0:
        print("Result  : FAILED (Ungrounded LLM passed a non-existent chemical)")
    
    print("\n--- TEST 4: Grounded Environment (Non-existent Chemical) ---")
    feedback = real_env.evaluate(state=nonexistent_plan)
    print(f"Score   : {feedback.score}")
    print(f"Feedback: {feedback.details[0]}")
    if not feedback.success:
        print("Result  : SUCCESS (Grounded environment rejected the non-existent chemical)")
    print("--------------------------------------------------\n")


if __name__ == "__main__":
    run_demonstration()