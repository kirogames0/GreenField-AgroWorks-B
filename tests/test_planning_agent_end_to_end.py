import json

from planning.planning_agent import (
    build_demo_summary,
    grounded_failure_detail,
    run_end_to_end_demo,
)
from planning.planning_lab.algorithms.environment import Environment


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def invoke(self, messages, temperature=0.2):
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError("No fake response left for the model")
        response = self.responses.pop(0)

        class Response:
            content = response

        return Response()

    def with_structured_output(self, model_cls=None, method=None, include_raw=False):
        return self


def test_grounded_failure_detail_detects_bad_write():
    detail = grounded_failure_detail({"worker_id": "w999", "chemical_id": "chem2"}, Environment())
    assert detail
    assert "certified" in detail.lower() or "worker" in detail.lower()


def test_run_end_to_end_demo_builds_a_complete_summary():
    llm = FakeLLM([
        "Plan: check field, verify inventory, confirm compliance, submit request.",
        "Next task: check inventory and compliance before acting.",
        "Next task: check worker certification before submitting.",
        "Next task: send a compliant action.",
        "Next task: final review.",
        "I missed the certified worker requirement.",
        "I forgot to verify worker certification.",
        "I should validate worker certification before retrying.",
        "I corrected the worker requirement and will resubmit with the right identity.",
        "I corrected the worker requirement and will resubmit with the right identity.",
        "I corrected the worker requirement and will resubmit with the right identity.",
        "I corrected the worker requirement and will resubmit with the right identity.",
        "I corrected the worker requirement and will resubmit with the right identity.",
        "I corrected the worker requirement and will resubmit with the right identity.",
        "I corrected the worker requirement and will resubmit with the right identity.",
        "I corrected the worker requirement and will resubmit with the right identity.",
        "I corrected the worker requirement and will resubmit with the right identity.",
        "I corrected the worker requirement and will resubmit with the right identity.",
        "I corrected the worker requirement and will resubmit with the right identity.",
    ])

    summary = run_end_to_end_demo(llm=llm, field_id="f1")

    assert summary["goal"] == "Prepare field f1 for a pesticide application"
    assert "static_plan" in summary
    assert "dynamic_plan" in summary
    assert "routed_subtasks" in summary
    assert "self_refine" in summary
    assert "reflexion" in summary
    assert "grounded_failure" in summary
    assert isinstance(summary["routed_subtasks"], dict)
    assert any("plan_and_solve" in str(value) for value in summary["routed_subtasks"].values())
    detail = summary["grounded_failure"]["detail"].lower()
    assert "worker" in detail
    assert "certified" in detail or "not found" in detail
    assert summary["self_refine"]["revised"]
