from .base import Msg, approx_tokens


def zone_based_pruning(messages: list[Msg], num_zones: int = 4) -> list[Msg]:
    """
    Split transcript into `num_zones` equal zones by position. Oldest
    zone: keep only tool-output-stripped dialogue (heaviest prune).
    Middle zones: keep dialogue + one-line tool summaries.
    Most recent zone: keep everything raw.
    This is a middle ground between sliding window (loses old detail
    entirely) and full summarization (LLM cost on every chunk).
    """
    if not messages:
        return []

    n = len(messages)
    zone_size = max(1, n // num_zones)
    zones = [messages[i:i + zone_size] for i in range(0, n, zone_size)]

    result = []
    for zone_idx, zone in enumerate(zones):
        is_last_zone = (zone_idx == len(zones) - 1)
        if is_last_zone:
            result.extend(zone)  # keep raw
        elif zone_idx == 0:
            # oldest zone: drop tool messages entirely, keep dialogue
            result.extend(m for m in zone if m.role != "tool")
        else:
            # middle zones: compress tool messages to one-line stubs
            for m in zone:
                if m.role == "tool":
                    result.append(Msg("tool", m.content[:80] + "..."))
                else:
                    result.append(m)
    return result


def run(messages: list[Msg], num_zones: int = 4) -> dict:
    pruned = zone_based_pruning(messages, num_zones)
    input_tokens = sum(approx_tokens(m.content) for m in pruned)
    return {
        "strategy": "zone_based_pruning",
        "pruned_messages": pruned,
        "input_tokens": input_tokens,
        "output_tokens": 0,
        "llm_calls": 0,
    }
