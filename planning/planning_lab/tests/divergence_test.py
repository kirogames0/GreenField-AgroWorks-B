"""
Evaluates Decomposition-First versus Dynamic Decomposition architectures.
Demonstrates execution divergence when encountering mid-plan failures.
"""

import time
from langchain_openai import ChatOpenAI
from planning.planning_lab.algorithms.decomposition import decompose_goal, execute_plan, final_output
from planning.planning_lab.algorithms.dynamic_decomposition import dynamic_decomposition
import os

def parse_dynamic_metrics(metrics_str: str) -> tuple[int, int]:
    """Parses the token and call count string returned by dynamic_decomposition."""
    try:
        parts = metrics_str.split('|')
        tokens = int(parts[0].split(':')[1])
        calls = int(parts[1].split(':')[1])
        return tokens, calls
    except Exception:
        return 0, 0

def run_divergence_evaluation():
    print("--------------------------------------------------")
    print("DIVERGENCE EVALUATION: STATIC VS. DYNAMIC DAG")
    print("--------------------------------------------------")

    # Prompt designed to guarantee a database failure mid-plan
    prompt = """Emergency: Schedule an application of Restricted Chemical 2 (chem2) on Field 1 using Worker 999 (w999). 
        CRITICAL: Whenever you output JSON to execute an action, you MUST use the exact keys 'worker_id' and 'chemical_id'."""
    print(f"Goal: {prompt}\n")

    llm = ChatOpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        model=os.environ["LLM_MODEL_NAME"],
        max_retries=5
    )

    # --- 1. Decomposition-First (Static DAG) ---
    print("--- 1. Decomposition-First (Static DAG) ---")
    static_calls = 0
    static_tokens = 0
    static_success = False

    start_time_static = time.perf_counter()
    try:
        # Step 1: Generate full plan upfront
        plan = decompose_goal(prompt, llm)
        static_calls += 1

        # Step 2: Execute plan blindly
        outputs = execute_plan(plan, llm, max_workers=1)

        # Extract injected metrics
        metrics = outputs.pop("_metrics", {"tokens": 0, "calls": 0})
        static_tokens = metrics.get("tokens", 0)
        static_calls += metrics.get("calls", 0)

        final_res = final_output(plan, outputs)
        print("Final Output Synthesis:\n", final_res)

        if any(err in final_res for err in ["Error", "Violation", "not found", "Formatting"]):
            static_success = False
        else:
            static_success = True

    except Exception as e:
        print(f"Execution Error: {e}")
        static_success = False

    latency_static = time.perf_counter() - start_time_static
    print(f"Metrics: {static_calls} calls, {static_tokens} tokens, {latency_static:.2f}s\n")


    # --- 2. Dynamic Decomposition (Interleaved) ---
    print("--- 2. Dynamic Decomposition (Interleaved) ---")
    dynamic_calls = 0
    dynamic_tokens = 0
    dynamic_success = False

    start_time_dynamic = time.perf_counter()
    try:
        # Step 1: Generate and execute nodes sequentially, reflecting on environment feedback
        history = dynamic_decomposition(prompt, llm)

        # Extract injected metrics from the final history tuple
        metric_tuple = history.pop() if history and history[-1][0] == "_metrics" else None
        if metric_tuple:
            dynamic_tokens, dynamic_calls = parse_dynamic_metrics(metric_tuple[1])

        final_task, final_res = history[-1] if history else ("None", "No result")
        print(f"Final Task Execution:\n{final_task}")
        print(f"Final Output:\n{final_res}")


        if any(err in final_res for err in ["Error", "Violation"]) and not any(task for task, _ in history if
                                                                               "search" in task.lower() or "list" in task.lower() or "find" in task.lower()):
            dynamic_success = False
        else:
            dynamic_success = True

    except Exception as e:
        print(f"Execution Error: {e}")
        dynamic_success = False

    latency_dynamic = time.perf_counter() - start_time_dynamic
    print(f"Metrics: {dynamic_calls} calls, {dynamic_tokens} tokens, {latency_dynamic:.2f}s\n")


    # --- 3. Comparison Table ---
    print("--------------------------------------------------")
    print("DIVERGENCE COMPARISON TABLE")
    print("--------------------------------------------------")
    print(f"| Method              | Success | LLM Calls | Tokens | Latency |")
    print(f"|---------------------|---------|-----------|--------|---------|")
    print(f"| Decomposition-First | {str(static_success):<7} | {static_calls:<9} | {static_tokens:<6} | {latency_static:.2f}s   |")
    print(f"| Dynamic Decomp      | {str(dynamic_success):<7} | {dynamic_calls:<9} | {dynamic_tokens:<6} | {latency_dynamic:.2f}s   |")
    print("--------------------------------------------------")

if __name__ == "__main__":
    run_divergence_evaluation()