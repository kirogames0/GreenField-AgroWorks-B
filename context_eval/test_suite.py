"""
Fixed long-context test suite. Per the lab's cost note: input tokens
are cheap, so transcripts lean HEAVY on large synthetic tool-output
noise rather than trying to generate lots of model output.

Mirrors our real system's actual failure mode: a REI/restricted-
chemical fact stated early gets buried under many check_field_status /
get_inventory tool calls before a later question needs it.

DO NOT MODIFY after evaluation starts (lab guardrail) -- fixed set,
seeded, deterministic.
"""

import random
from strategies.base import Msg

CRITICAL_FACT = (
    "Field f1 was treated with chem2 (a restricted-use pesticide) on "
    "2026-07-01 with a 24-hour re-entry interval."
)

FINAL_QUERY = "Before we schedule anyone onto f1 today, any re-entry restrictions I should know about?"

TOOL_NOISE_TEMPLATES = [
    "get_inventory result: {{'chemical_id': 'chem{n}', 'quantity_on_hand': {qty}, 'unit': 'lbs'}}",
    "check_field_status result: {{'field_id': 'f{n}', 'crop': 'lettuce', 'crop_stage': 'seedling'}}",
    "authenticate result: {{'worker_id': 'w{n}', 'role': 'field_hand'}}",
]


def _make_noise_message(rng: random.Random, i: int) -> Msg:
    template = rng.choice(TOOL_NOISE_TEMPLATES)
    content = template.format(n=i % 9 + 1, qty=rng.randint(10, 500))
    return Msg("tool", content)


def generate_transcript(seed: int, num_noise_messages: int = 34) -> list[Msg]:
    """
    Structure: [user states critical fact] -> [lots of tool noise] ->
    [final user query needing the fact]. Matches the lab's worked
    example shape (allergy detail at turn 3, needed at turn 40).
    """
    rng = random.Random(seed)
    transcript = [
        Msg("user", f"Heads up -- {CRITICAL_FACT}"),
        Msg("assistant", "Noted, thanks for flagging that."),
    ]
    for i in range(num_noise_messages):
        transcript.append(_make_noise_message(rng, i))
    transcript.append(Msg("user", FINAL_QUERY))
    return transcript


def generate_test_suite(num_variations: int = 10) -> list[list[Msg]]:
    return [generate_transcript(seed=s) for s in range(num_variations)]


def detail_survived(pruned_messages: list[Msg]) -> bool:
    """
    Scoring function: did the critical fact (or a recognizable
    summary of it) survive pruning? Checks for the key markers
    (field id + chemical id + '24' hour figure) rather than exact
    string match, since summarization strategies paraphrase.
    """
    combined = " ".join(m.content for m in pruned_messages).lower()
    markers = ["f1", "chem2", "24"]
    return all(marker in combined for marker in markers)
