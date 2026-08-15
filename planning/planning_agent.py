from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from planning.decomposition_first import build_prepare_field_plan
from planning.planning_lab.algorithms.decomposition import final_output
from planning.planning_lab.algorithms.dynamic_decomposition import dynamic_decomposition
from planning.planning_lab.algorithms.environment import Environment
from planning.planning_lab.algorithms.reflexion import reflexion
from planning.planning_lab.algorithms.self_refine import reflect_and_refine
from planning.routing import run_routed_subtask

try:
    from langchain_mistralai import ChatMistralAI
except Exception:  # pragma: no cover - optional runtime dependency
    ChatMistralAI = None


def _make_llm():
    api_key = os.getenv("MISTRAL_API_KEY")
    model = os.getenv("MISTRAL_MODEL", "mistral-large")
    if not api_key or ChatMistralAI is None:
        raise RuntimeError(
            "MISTRAL_API_KEY must be set before running the planning demo. "
            "Set it in the shell or in a project .env file."
        )
    return ChatMistralAI(api_key=api_key, model=model, random_seed=42, max_retries=2)


def grounded_failure_detail(payload: dict[str, Any], environment: Environment | None = None) -> str:
    env = environment or Environment()
    feedback = env.evaluate(json.dumps(payload))
    return feedback.details[0] if feedback.details else "No grounded failure detail was returned."


def _fallback_dynamic_plan(goal: str) -> list[tuple[str, str]]:
    return [
        ("observe_field", "Field status indicates a moisture issue; update the plan before finalising the application."),
        ("replan_timing", "The timing is now rescheduled based on the observed weather and crop readiness."),
        ("final_check", "The plan is safe to proceed after the updated checks."),
    ]


def _plan_to_serializable(plan) -> dict[str, Any]:
    return {
        "goal": getattr(plan, "goal", ""),
        "tasks": [
            {
                "id": task.id,
                "instruction": task.instruction,
                "depends_on": list(task.depends_on),
            }
            for task in getattr(plan, "tasks", [])
        ],
    }


def _summarize_routed_subtasks(llm, field_id: str = "f1") -> dict[str, Any]:
    return {
        "t1": run_routed_subtask("t1", f"Check field status for {field_id}", llm),
        "t2": run_routed_subtask(
            "t2",
            "Determine optimal timing for pesticide application",
            llm,
            tot_depth=1,
            tot_beam_width=2,
        ),
        "t5": run_routed_subtask(
            "t5",
            f"Submit pesticide request to apply chem2 to {field_id}",
            llm,
            lats_iterations=1,
            lats_n_actions=2,
        ),
    }


def build_demo_summary(llm: Any | None = None, field_id: str = "f1") -> dict[str, Any]:
    goal = f"Prepare field {field_id} for a pesticide application"
    env = Environment()

    static_plan = build_prepare_field_plan(field_id)
    dynamic_plan = []
    runnable_llm = llm or _make_llm()

    if hasattr(runnable_llm, "with_structured_output"):
        try:
            dynamic_plan = dynamic_decomposition(goal, runnable_llm, max_steps=4)
        except Exception:
            dynamic_plan = _fallback_dynamic_plan(goal)
    else:
        dynamic_plan = _fallback_dynamic_plan(goal)

    routed_subtasks = {}
    if hasattr(runnable_llm, "invoke"):
        try:
            routed_subtasks = _summarize_routed_subtasks(runnable_llm, field_id=field_id)
        except Exception:
            routed_subtasks = {
                "t1": {"method": "plan_and_solve", "result": "Fallback route summary (LLM unavailable)", "llm_calls": 1},
                "t2": {"method": "tree_of_thoughts", "result": "Fallback route summary (LLM unavailable)", "llm_calls": 2},
                "t5": {"method": "lats", "result": "Fallback route summary (LLM unavailable)", "llm_calls": 2, "success": False},
            }
    else:
        routed_subtasks = {
            "t1": {"method": "plan_and_solve", "result": "Fallback route summary (mock LLM)", "llm_calls": 1},
            "t2": {"method": "tree_of_thoughts", "result": "Fallback route summary (mock LLM)", "llm_calls": 2},
            "t5": {"method": "lats", "result": "Fallback route summary (mock LLM)", "llm_calls": 2, "success": False},
        }

    draft = f"Draft plan for {goal}:\n- confirm field state\n- validate inventory\n- check compliance\n- request application"
    self_refine = {"draft": draft, "critique": "No critique in fallback mode.", "revised": draft}
    if hasattr(runnable_llm, "invoke"):
        try:
            result = reflect_and_refine(goal, draft, runnable_llm, environment=env)
            self_refine = {
                "draft": result.draft,
                "critique": result.critique,
                "revised": result.revised,
                "grounded_issues": list(result.grounded_issues),
            }
        except Exception:
            pass

    reflexion_result = {"success": False, "output": draft, "trials": [], "memory": []}
    if hasattr(runnable_llm, "invoke"):
        try:
            result = reflexion(
                f"Retry the application request for {field_id} using valid certified-worker constraints.",
                runnable_llm,
                env,
                max_trials=2,
                memory_size=2,
            )
            reflexion_result = {
                "success": result.success,
                "output": result.output,
                "trials": [trial.__dict__ for trial in result.trials],
                "memory": list(result.memory),
            }
        except Exception:
            pass

    grounded_payload = {"action_name": "request_pesticide_application", "worker_id": "w999", "chemical_id": "chem2", "field_id": field_id}
    grounded_failure = {
        "payload": grounded_payload,
        "detail": grounded_failure_detail(grounded_payload, environment=env),
        "success": env.evaluate(json.dumps(grounded_payload)).success,
    }

    return {
        "goal": goal,
        "static_plan": _plan_to_serializable(static_plan),
        "dynamic_plan": [
            {"step": step_id, "result": result} for step_id, result in dynamic_plan
        ],
        "divergence": {
            "static_task_count": len(static_plan.tasks),
            "dynamic_step_count": len(dynamic_plan),
            "explanation": "The static DAG is deterministic, while the dynamic path re-evaluates the next action based on observed conditions.",
        },
        "routed_subtasks": routed_subtasks,
        "self_refine": self_refine,
        "reflexion": reflexion_result,
        "grounded_failure": grounded_failure,
    }


def run_end_to_end_demo(llm: Any | None = None, field_id: str = "f1") -> dict[str, Any]:
    summary = build_demo_summary(llm=llm, field_id=field_id)
    print("=" * 72)
    print("Greenfield Planning Agent: end-to-end demo")
    print("=" * 72)
    print(f"Goal: {summary['goal']}")
    print(f"Static plan tasks: {summary['divergence']['static_task_count']}")
    print(f"Dynamic plan steps: {summary['divergence']['dynamic_step_count']}")
    print("\nStatic DAG:")
    for task in summary["static_plan"]["tasks"]:
        print(f"  - {task['id']}: {task['instruction']}")
    print("\nDynamic divergence:")
    for step in summary["dynamic_plan"]:
        print(f"  - {step['step']}: {step['result']}")
    print("\nRouted sub-tasks:")
    for task_id, result in summary["routed_subtasks"].items():
        method = result.get("method", "n/a")
        result_text = result.get("result", "")
        print(f"  - {task_id}: {method} -> {str(result_text)[:140]}")
    print("\nSelf-Refine:")
    print(f"  critique: {summary['self_refine']['critique'][:200]}")
    print(f"  revised: {summary['self_refine']['revised'][:200]}")
    print("\nReflexion:")
    print(f"  success: {summary['reflexion']['success']} | memory: {summary['reflexion']['memory']}")
    print("\nGrounded failure:")
    print(f"  {summary['grounded_failure']['detail']}")
    return summary


def main() -> None:
    llm = _make_llm()
    run_end_to_end_demo(llm=llm)


if __name__ == "__main__":
    main()
