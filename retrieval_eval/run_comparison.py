from typing import Dict, List, Any
from mcp_server.rag.naive_rag import run_naive_rag
from mcp_server.rag.hybrid_search import run_hybrid_search
from mcp_server.rag.agentic_rag import run_agentic_rag
from retrieval_eval.test_questions import TEST_QUESTIONS


def evaluate_accuracy(results: List[Dict[str, Any]], expected_keywords: List[str]) -> bool:

    if not results:
        return False

    combined_text = " ".join(
        [doc.get("payload", doc.get("text", "")).lower() for doc in results]
    )

    # Require at least 50% of expected keywords to be present in retrieved context
    matched = sum(1 for kw in expected_keywords if kw.lower() in combined_text)
    return (matched / len(expected_keywords)) >= 0.50


def run_benchmark():
    print("=" * 70)
    print("Running Retrieval Architecture Benchmark Suite...")
    print("=" * 70)

    architectures = [
        ("Naive RAG", run_naive_rag),
        ("Hybrid Search", run_hybrid_search),
        ("Agentic RAG", run_agentic_rag),
    ]

    metrics: Dict[str, Dict[str, Any]] = {
        name: {"correct": 0, "total": len(TEST_QUESTIONS), "tokens": 0, "latency": 0.0}
        for name, _ in architectures
    }

    for q in TEST_QUESTIONS:
        print("\n" + "=" * 70)
        print(f"Testing Question [{q['id']}] ({q['category']}):")
        print(f"   Query: '{q['query']}'")
        print("=" * 70)

        for arch_name, arch_fn in architectures:
            try:
                output = arch_fn(query=q["query"], top_k=3)
                results = output.get("results", [])
                tokens = output.get("tokens_used", 0)
                latency = output.get("latency", 0.0)

                is_correct = evaluate_accuracy(results, q["expected_keywords"])
                if is_correct:
                    metrics[arch_name]["correct"] += 1

                metrics[arch_name]["tokens"] += tokens
                metrics[arch_name]["latency"] += latency

                status = "PASS" if is_correct else " FAIL"

                print(f"\n   🔹 Architecture: {arch_name} | Status: {status} | Latency: {latency:.4f}s | Tokens: {tokens}")
                print("   " + "-" * 60)

                if not results:
                    print("      [No results returned]")
                else:
                    for idx, doc in enumerate(results, 1):
                        section = doc.get("metadata", {}).get("section", doc.get("section", "N/A"))
                        text = doc.get("payload", doc.get("text", "")).strip().replace("\n", " ")
                        print(f"      [{idx}] Section : {section}")
                        print(f"          Snippet : {text}")

            except Exception as e:
                print(f"\n   {arch_name:<15}: ERROR ({e})")

    # Generate Markdown Summary Table
    num_q = len(TEST_QUESTIONS)
    print("\n" + "=" * 70)
    print("FINAL BENCHMARK COMPARISON TABLE (Copy into README.md)")
    print("=" * 70 + "\n")

    markdown_table = [
        "| Architecture | Accuracy | Avg Tokens / Query | Avg Latency / Query | Shipped Status |",
        "|---|---|---|---|---|",
    ]

    for arch_name, _ in architectures:
        m = metrics[arch_name]
        accuracy_str = f"{m['correct']}/{m['total']} ({(m['correct']/m['total'])*100:.0f}%)"
        avg_tokens = f"{m['tokens'] / num_q:.1f}"
        avg_latency = f"{m['latency'] / num_q:.3f}s"
        shipped = "**Shipped Default**" if arch_name == "Hybrid Search" else "Available (Escalation)" if arch_name == "Agentic RAG" else "Baseline"

        markdown_table.append(
            f"| **{arch_name}** | {accuracy_str} | {avg_tokens} | {avg_latency} | {shipped} |"
        )

    print("\n".join(markdown_table))
    print("\n" + "=" * 70)


if __name__ == "__main__":
    run_benchmark()