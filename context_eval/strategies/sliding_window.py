from .base import Msg, approx_tokens


def sliding_window(messages: list[Msg], keep_last: int = 10) -> list[Msg]:
    """Keep only the most recent `keep_last` messages. Cheapest,
    weakest at retaining early buried detail."""
    return messages[-keep_last:]


def run(messages: list[Msg], keep_last: int = 10) -> dict:
    pruned = sliding_window(messages, keep_last)
    input_tokens = sum(approx_tokens(m.content) for m in pruned)
    return {
        "strategy": "sliding_window",
        "pruned_messages": pruned,
        "input_tokens": input_tokens,
        "output_tokens": 0,   # no LLM call needed for this strategy
        "llm_calls": 0,
    }
