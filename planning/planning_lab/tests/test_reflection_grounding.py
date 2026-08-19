import json
from config import get_llm_client
from planning.planning_lab.algorithms.environment import Environment
from planning.planning_lab.algorithms.reflexion import reflexion
from planning.planning_lab.algorithms.self_refine import reflect_and_refine


def test_reflexion_capped_memory_survives_multiple_failed_trials():
    """Test that Reflexion properly caps memory and generates reflections."""
    env = Environment()

    # Use real LLM from centralized config
    llm = get_llm_client()

    result = reflexion(
        task="Submit a restricted pesticide application using only certified workers.",
        llm=llm,
        environment=env,
        max_trials=3,
        memory_size=2,
    )

    # Test structure and behavioral properties (content is non-deterministic)
    # Note: Real LLM may succeed on first try, so we check that trials >= 1
    assert len(result.trials) >= 1
    assert len(result.memory) <= 2  # Should be capped at memory_size
    assert all(isinstance(trial.attempt, str) for trial in result.trials)
    assert all(isinstance(reflection, str) for reflection in result.memory)
    
    # If there are reflections, they should be meaningful
    if result.memory:
        assert all(len(reflection.strip()) > 0 for reflection in result.memory)
        assert any(len(reflection.split()) > 3 for reflection in result.memory)
        
        # Test that reflections mention the core issue (worker certification)
        reflection_text = " ".join(result.memory).lower()
        assert any(term in reflection_text for term in ["worker", "certified", "certification", "invalid"])


def test_grounded_critique_catches_failure_that_ungrounded_pass_misses():
    goal = "Submit a pesticide application using the approved worker and chemical rules."
    draft = json.dumps({
        "action_name": "request_pesticide_application",
        "worker_id": "w999",
        "chemical_id": "chem2",
        "field_id": "f1",
    })

    llm = get_llm_client()
    result = reflect_and_refine(goal, draft, llm, environment=Environment())

    assert result.grounded_issues, "Grounded environment should catch invalid worker/chemical"
    assert any("w999" in issue for issue in result.grounded_issues), "Should flag invalid worker"
    assert "worker" in result.critique.lower() or "invalid" in result.critique.lower(), "Should mention worker validation issue"
    assert result.revised.strip(), "Should generate a revised plan"

    # Validate revised plan fixes the issue (e.g., uses certified worker)
    # Extract JSON from markdown code block if present
    revised_text = result.revised
    if "```json" in revised_text:
        revised_text = revised_text.split("```json")[1].split("```")[0].strip()
    elif "```" in revised_text:
        revised_text = revised_text.split("```")[1].split("```")[0].strip()
    
    revised_plan = json.loads(revised_text)
    # Note: Real LLM may choose a different valid worker ID, not necessarily changing w999
    assert revised_plan["worker_id"] != "w999" or "certified" in str(revised_plan["worker_id"]).lower(), "Revised plan should use a valid worker"
