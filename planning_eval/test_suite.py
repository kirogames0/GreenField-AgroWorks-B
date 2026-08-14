from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalCase:
    name: str
    goal: str
    category: str
    preferred_method: str
    rationale: str


def fixed_suite() -> list[EvalCase]:
    """Deterministic evaluation cases; fixed once evaluation starts."""
    return [
        EvalCase(
            name="decomposition_first_prefers_static_plan",
            goal="Prepare field f1 for a pesticide application.",
            category="decomposition",
            preferred_method="decomposition_first",
            rationale="A fixed dependency chain and real tool routing make the work deterministic and should be planned once.",
        ),
        EvalCase(
            name="dynamic_handles_unfolding_state",
            goal="Decide the next safe action after an unexpected field-status change and weather warning.",
            category="dynamic",
            preferred_method="dynamic",
            rationale="The best next step depends on evolving observations, so re-planning mid-stream is cheaper than committing to a rigid DAG.",
        ),
        EvalCase(
            name="lookahead_lats_for_write_action",
            goal="Submit a restricted pesticide application under uncertain worker certification and inventory constraints.",
            category="lookahead",
            preferred_method="lats",
            rationale="The action is a costly write with real external feedback; candidates must be explored before committing.",
        ),
        EvalCase(
            name="reflexion_memory_across_trials",
            goal="Retry a restricted pesticide application until the worker and chemical constraints are satisfied.",
            category="reflexion",
            preferred_method="reflexion",
            rationale="The next attempt depends on remembered cross-trial failure details, not just the latest output text.",
        ),
    ]


def validate_suite() -> None:
    suite = fixed_suite()
    assert len(suite) == 4, "Fixed suite must contain exactly four cases."
    names = {case.name for case in suite}
    assert len(names) == 4, "Suite case names must be unique."
    required = {
        "decomposition_first_prefers_static_plan",
        "dynamic_handles_unfolding_state",
        "lookahead_lats_for_write_action",
        "reflexion_memory_across_trials",
    }
    missing = required - names
    assert not missing, f"Missing required cases: {sorted(missing)}"
