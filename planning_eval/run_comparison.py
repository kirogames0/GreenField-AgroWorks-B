from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from planning.planning_lab.algorithms.decomposition import decompose_goal, execute_plan, final_output
from planning.planning_lab.algorithms.dynamic_decomposition import dynamic_decomposition
from planning.planning_lab.algorithms.environment import Environment
from planning.planning_lab.algorithms.lats import lats
from planning.planning_lab.algorithms.plan_and_solve import plan_and_solve
from planning.planning_lab.algorithms.reflexion import reflexion
from planning.planning_lab.algorithms.self_refine import reflect_and_refine
from planning.planning_lab.algorithms.tree_of_thoughts import tree_of_thoughts
from planning_eval.test_suite import fixed_suite, validate_suite


@dataclass
class ComparisonResult:
    case: str
    method: str
    task_success: bool
    accuracy: float
    llm_calls: int
    tokens: int
    latency_s: float
    cost: float
    trace: list[dict[str, Any]]


def _run_method(method_name: str, case: Any, llm: Any) -> tuple[bool, float, int, int, float, list[dict[str, Any]], float]:
    env = Environment()
    start = time.perf_counter()
    trace: list[dict[str, Any]] = []
    task_success = False
    accuracy = 0.0
    llm_calls = 0
    tokens = 0
    cost = 0.0

    if method_name == "decomposition_first":
        plan = decompose_goal(case.goal, llm)
        outputs = execute_plan(plan, llm)
        final = final_output(plan, outputs)
        task_success = "error" not in str(final).lower() and "violation" not in str(final).lower()
        accuracy = 1.0 if task_success else 0.0
        metrics = outputs.pop("_metrics", {"tokens": 0, "calls": 0})
        llm_calls = int(metrics.get("calls", 0))
        tokens = int(metrics.get("tokens", 0))
        trace = [{"step": "decompose_goal", "goal": case.goal}, {"step": "execute_plan", "summary": str(final)[:200]}]

    elif method_name == "dynamic":
        history = dynamic_decomposition(case.goal, llm)
        task_success = any("environment validation" in str(item[1]).lower() for item in history)
        accuracy = 1.0 if task_success else 0.0
        metrics = history.pop() if history and history[-1][0] == "_metrics" else ("_metrics", "tokens:0|calls:0")
        _, metric_text = metrics
        llm_calls = int(metric_text.split("calls:")[-1])
        tokens = int(metric_text.split("tokens:")[-1].split("|")[0])
        trace = [{"step": "dynamic_decomposition", "history": history}]

    elif method_name == "plan_and_solve":
        result = plan_and_solve(case.goal, llm)
        task_success = bool(result)
        accuracy = 1.0 if task_success else 0.0
        llm_calls = 1
        tokens = 0
        trace = [{"step": "plan_and_solve", "result": result}]

    elif method_name == "tree_of_thoughts":
        thoughts = tree_of_thoughts(case.goal, llm, depth=2, beam_width=2)
        result = thoughts[0].state if thoughts else "No candidate"
        task_success = bool(result)
        accuracy = 1.0 if task_success else 0.0
        llm_calls = 2 * 2 * 2
        tokens = 0
        trace = [{"step": "tree_of_thoughts", "best": result}]

    elif method_name == "lats":
        outcome = lats(case.goal, llm, env, iterations=2, n_actions=2)
        task_success = outcome.success
        accuracy = 1.0 if task_success else 0.0
        llm_calls = outcome.iterations * 2 * 2
        tokens = 0
        trace = [{"step": "lats", "best": outcome.output, "best_score": outcome.best_score}]

    elif method_name == "self_refine":
        draft = "Draft: " + case.goal
        result = reflect_and_refine(case.goal, draft, llm, environment=env)
        task_success = bool(result.revised) and not result.grounded_issues
        accuracy = 1.0 if task_success else 0.0
        llm_calls = 2
        tokens = 0
        trace = [{"step": "self_refine", "critique": result.critique, "revised": result.revised}]

    elif method_name == "reflexion":
        result = reflexion(case.goal, llm, env, max_trials=3, memory_size=2)
        task_success = result.success
        accuracy = 1.0 if task_success else 0.0
        llm_calls = len(result.trials) * 2
        tokens = 0
        trace = [{"step": "reflexion", "memory": result.memory, "trials": [trial.__dict__ for trial in result.trials]}]

    else:
        raise ValueError(f"Unknown method: {method_name}")

    latency = time.perf_counter() - start
    cost = llm_calls * 0.001 + tokens / 1000 * 0.002
    return task_success, accuracy, llm_calls, tokens, latency, trace, cost


def render_table(rows: list[ComparisonResult]) -> str:
    header = (
        f"{'Case':<30} {'Method':<18} {'Acc':>6} {'Success':>8} {'Calls':>8} {'Tokens':>10} {'Latency(s)':>12} {'Cost':>10}"
    )
    lines = [header, "-" * len(header)]
    for row in rows:
        lines.append(
            f"{row.case:<30} {row.method:<18} {row.accuracy:>6.2f} {str(row.task_success):>8} {row.llm_calls:>8} {row.tokens:>10} {row.latency_s:>12.3f} {row.cost:>10.4f}"
        )
    return "\n".join(lines)


def run_suite(llm: Any) -> list[ComparisonResult]:
    validate_suite()
    results: list[ComparisonResult] = []
    for case in fixed_suite():
        for method_name in [
            "decomposition_first",
            "dynamic",
            "plan_and_solve",
            "tree_of_thoughts",
            "lats",
            "self_refine",
            "reflexion",
        ]:
            success, accuracy, llm_calls, tokens, latency, trace, cost = _run_method(method_name, case, llm)
            results.append(
                ComparisonResult(
                    case=case.name,
                    method=method_name,
                    task_success=success,
                    accuracy=accuracy,
                    llm_calls=llm_calls,
                    tokens=tokens,
                    latency_s=latency,
                    cost=cost,
                    trace=trace,
                )
            )
    return results


def write_artifacts(rows: list[ComparisonResult], output_dir: str = "planning_eval/artifacts") -> list[str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    artifact_paths: list[str] = []
    for row in rows:
        file_path = output_path / f"{row.case}_{row.method}.json"
        file_path.write_text(json.dumps(asdict(row), indent=2), encoding="utf-8")
        artifact_paths.append(str(file_path))
    return artifact_paths


if __name__ == "__main__":
    print("planning_eval comparisons require a project LLM implementation bound to the local planner.")
    print("This harness is intentionally structured to emit the same artifact/trace rows that the planner uses for comparison tables.")
