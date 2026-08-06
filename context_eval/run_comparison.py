"""
Runs all four context-management strategies against the same fixed
test suite and produces the comparison table the README cites.

Usage: python run_comparison.py
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from strategies import sliding_window, observation_masking, recursive_summarization, zone_based_pruning
from test_suite import generate_test_suite, detail_survived

STRATEGIES = {
    "sliding_window": lambda msgs: sliding_window.run(msgs, keep_last=10),
    "observation_masking": lambda msgs: observation_masking.run(msgs, keep_last_n_tool_outputs=3),
    "recursive_summarization": lambda msgs: recursive_summarization.run(msgs, chunk_size=15, keep_last_raw=5),
    "zone_based_pruning": lambda msgs: zone_based_pruning.run(msgs, num_zones=4),
}


def run_all(num_variations: int = 10):
    suite = generate_test_suite(num_variations)
    results = {}

    for strategy_name, strategy_fn in STRATEGIES.items():
        survived_count = 0
        total_input_tokens = 0
        total_output_tokens = 0
        total_latency = 0.0

        for transcript in suite:
            start = time.perf_counter()
            out = strategy_fn(transcript)
            elapsed = time.perf_counter() - start

            if detail_survived(out["pruned_messages"]):
                survived_count += 1
            total_input_tokens += out["input_tokens"]
            total_output_tokens += out["output_tokens"]
            total_latency += elapsed

        n = len(suite)
        results[strategy_name] = {
            "detail_recalled": f"{survived_count}/{n}",
            "avg_input_tokens": round(total_input_tokens / n),
            "avg_output_tokens": round(total_output_tokens / n),
            "avg_latency_s": round(total_latency / n, 4),
        }

    return results


def print_table(results: dict):
    header = f"{'Strategy':<26} {'Detail Recalled':<17} {'Avg Input Tok':<15} {'Avg Output Tok':<16} {'Avg Latency (s)':<16}"
    print(header)
    print("-" * len(header))
    for name, r in results.items():
        print(f"{name:<26} {r['detail_recalled']:<17} {r['avg_input_tokens']:<15} {r['avg_output_tokens']:<16} {r['avg_latency_s']:<16}")


if __name__ == "__main__":
    results = run_all()
    print_table(results)
