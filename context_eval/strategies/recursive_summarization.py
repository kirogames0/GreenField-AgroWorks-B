from .base import Msg, approx_tokens


def _default_extractive_summary(chunk: list[Msg]) -> str:
    """
    Deterministic offline stand-in for a real LLM summarization call
    (no network/API access in this environment). It takes the first
    sentence of every message in the chunk, on the (weak) theory that
    the earliest-stated fact in a chunk is more likely load-bearing.
    SWAP THIS for a real LLM call before grading:
        summary = llm_client.chat(f"Summarize concisely: {chunk_text}")
    Keep the function signature identical so run() doesn't change.
    """
    parts = []
    for m in chunk:
        first_sentence = m.content.split(".")[0][:200]
        parts.append(f"[{m.role}] {first_sentence}")
    return "SUMMARY: " + " | ".join(parts)


def recursive_summarization(
    messages: list[Msg],
    chunk_size: int = 15,
    keep_last_raw: int = 5,
    summarize_fn=_default_extractive_summary,
) -> tuple[list[Msg], int]:
    """
    Compact every `chunk_size` older messages into one summary message,
    keep the most recent `keep_last_raw` messages un-summarized.
    Returns (pruned_messages, llm_calls_made).
    """
    if len(messages) <= keep_last_raw:
        return list(messages), 0

    to_summarize = messages[:-keep_last_raw]
    recent = messages[-keep_last_raw:]

    summarized = []
    llm_calls = 0
    for i in range(0, len(to_summarize), chunk_size):
        chunk = to_summarize[i:i + chunk_size]
        summary_text = summarize_fn(chunk)
        llm_calls += 1
        summarized.append(Msg("assistant", summary_text))

    return summarized + recent, llm_calls


def run(messages: list[Msg], chunk_size: int = 15, keep_last_raw: int = 5, summarize_fn=_default_extractive_summary) -> dict:
    pruned, llm_calls = recursive_summarization(messages, chunk_size, keep_last_raw, summarize_fn)
    input_tokens = sum(approx_tokens(m.content) for m in pruned)
    # Each summarization call has its own input (the chunk) + output (the summary).
    # We count the summary text itself as "output tokens" produced by this strategy.
    output_tokens = sum(approx_tokens(m.content) for m in pruned if m.content.startswith("SUMMARY:"))
    return {
        "strategy": "recursive_summarization",
        "pruned_messages": pruned,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "llm_calls": llm_calls,
    }
