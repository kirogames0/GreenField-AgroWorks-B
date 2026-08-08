"""
Shared types for context_eval/. A "transcript" is a list of dicts:
{"role": "user"|"assistant"|"tool", "content": str}
Tool messages are the ones that bury early decisions under noise --
our test suite leans on those per the lab's cost note.
"""

from dataclasses import dataclass


@dataclass
class Msg:
    role: str
    content: str

    @staticmethod
    def from_dicts(dicts: list[dict]) -> list["Msg"]:
        return [Msg(d["role"], d["content"]) for d in dicts]


def approx_tokens(text: str) -> int:
    # Cheap deterministic stand-in for a real tokenizer (tiktoken etc).
    # ~4 chars/token is the standard rough estimate; good enough for a
    # relative comparison table across strategies run on the same text.
    return max(1, len(text) // 4)
