from config import get_llm_client
from planning.planning_agent import (
    grounded_failure_detail,
    run_end_to_end_demo,
)
from planning.planning_lab.algorithms.environment import Environment


def test_grounded_failure_detail_detects_bad_write():
    detail = grounded_failure_detail({"worker_id": "w999", "chemical_id": "chem2"}, Environment())
    assert detail
    assert "certified" in detail.lower() or "worker" in detail.lower()


def test_run_end_to_end_demo_builds_a_complete_summary():
    # Use real LLM from centralized config
    llm = get_llm_client()

    summary = run_end_to_end_demo(llm=llm, field_id="f1")

    # Test structure and behavioral properties (content is non-deterministic with real LLM)
    assert isinstance(summary["goal"], str)
    assert "static_plan" in summary
    assert "dynamic_plan" in summary
    assert "routed_subtasks" in summary
    assert "self_refine" in summary
    assert "reflexion" in summary
    assert "grounded_failure" in summary
    assert isinstance(summary["routed_subtasks"], dict)
    assert isinstance(summary["static_plan"]["tasks"], list)
    assert len(summary["static_plan"]["tasks"]) >= 3
    assert isinstance(summary["dynamic_plan"], list)
    assert len(summary["dynamic_plan"]) >= 3
    assert "critique" in summary["self_refine"]
    assert "revised" in summary["self_refine"]
    assert isinstance(summary["self_refine"]["revised"], str)
    assert "trials" in summary["reflexion"]
    assert "memory" in summary["reflexion"]
    assert isinstance(summary["grounded_failure"]["detail"], str)
    detail = summary["grounded_failure"]["detail"].lower()
    assert "worker" in detail or "certified" in detail
