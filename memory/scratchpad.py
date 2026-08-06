"""
Scratchpad -- agent's active working state, separate from the
message transcript. Pruning the transcript (short_term_buffer.py)
never touches this.

Real need: generate_compliance_report is multi-step (progress-tracked
tool call). If the transcript gets pruned mid-task, the agent must
still know "I'm waiting on a compliance report for f1, buyer request
came from turn 3" without re-reading pruned messages.
"""

from dataclasses import dataclass, field


@dataclass
class Scratchpad:
    current_plan: str | None = None       # e.g. "generate compliance report for f1"
    sub_goal: str | None = None           # e.g. "waiting on progress from generate_compliance_report"
    working_state: dict = field(default_factory=dict)  # arbitrary task-specific state

    def set_task(self, plan: str, sub_goal: str | None = None):
        self.current_plan = plan
        self.sub_goal = sub_goal

    def update_state(self, key: str, value):
        self.working_state[key] = value

    def clear(self):
        self.current_plan = None
        self.sub_goal = None
        self.working_state = {}

    def is_empty(self) -> bool:
        return self.current_plan is None and not self.working_state
