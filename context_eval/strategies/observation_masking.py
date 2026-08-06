from .base import Msg, approx_tokens

MASK_TEXT = "[tool output omitted -- superseded by later result]"


def mask_old_tool_outputs(messages: list[Msg], keep_last_n_tool_outputs: int = 3) -> list[Msg]:
    """
    Keep ALL dialogue (user/assistant) turns intact -- they're usually
    short -- but mask all but the most recent N tool-output messages,
    replacing their content with a short placeholder. This targets
    the actual failure mode when bloat is tool JSON, not conversation.
    """
    tool_indices = [i for i, m in enumerate(messages) if m.role == "tool"]
    keep_indices = set(tool_indices[-keep_last_n_tool_outputs:]) if tool_indices else set()

    result = []
    for i, m in enumerate(messages):
        if m.role == "tool" and i not in keep_indices:
            result.append(Msg("tool", MASK_TEXT))
        else:
            result.append(m)
    return result


def run(messages: list[Msg], keep_last_n_tool_outputs: int = 3) -> dict:
    pruned = mask_old_tool_outputs(messages, keep_last_n_tool_outputs)
    input_tokens = sum(approx_tokens(m.content) for m in pruned)
    return {
        "strategy": "observation_masking",
        "pruned_messages": pruned,
        "input_tokens": input_tokens,
        "output_tokens": 0,
        "llm_calls": 0,
    }
