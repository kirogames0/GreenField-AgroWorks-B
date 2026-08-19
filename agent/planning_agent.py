"""
Greenfield Planning Agent -- SEPARATE from agent.py's AgroWorksAgent
(memory/RAG agent). Per the lab: "a new agent, reusing the same
mcp_server/ and db/, sitting next to the agent you already built." This
file does not import from or modify agent.py, prompts.py, or
mistral_client.py's usage inside AgroWorksAgent -- it stands up its own
MCPClient connection and its own LLM calls via the toolkit's LangChain
interface.

Currently wires: Issue 1 (decomposition-first DAG -> real MCP tools).
Issue 2 (dynamic decomposition) and Issue 3 (PS/ToT/LATS routing) will
extend this same entrypoint without touching AgroWorksAgent.
"""

import asyncio
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "planning"))
# config.py lives in agent/ (confirmed via Get-ChildItem) -- SCRIPT_DIR
# IS agent/, since this file is agent/planning_agent.py, so it's
# already on sys.path via the insert below. Kept explicit for clarity.
sys.path.insert(0, SCRIPT_DIR)

from mcp_client import MCPClient
from decomposition_first import build_prepare_field_plan, execute_plan_against_mcp
from planning_lab.algorithms.decomposition import decompose_goal, final_output

from config import get_llm_client


async def run_fixed_demo_plan(client: MCPClient, field_id: str = "f1") -> None:
    """
    Runs the fixed reference plan from decomposition_first.py (deterministic
    DAG shape, useful for the demo transcript and for Issue 2's
    apples-to-apples divergence comparison against dynamic decomposition).
    """
    plan = build_prepare_field_plan(field_id)
    print(f"\nGoal: {plan.goal}")
    print(f"Execution batches: {plan.execution_batches()}\n")

    llm = get_llm_client()
    outputs = await execute_plan_against_mcp(plan, client, llm)

    for task_id, output in outputs.items():
        print(f"[{task_id}] {plan.task(task_id).instruction}")
        print(f"  -> {output}\n")

    terminal = plan.terminal_tasks()
    print("=" * 60)
    print("FINAL OUTPUT:", outputs[terminal[0]] if terminal else "(no terminal node)")


async def run_llm_generated_plan(client: MCPClient, goal: str) -> None:
    """
    Lets the toolkit's decompose_goal() (unmodified) generate the DAG
    shape from a free-text goal, then executes it through the same
    real-MCP execution path. Useful once the team wants to demo
    "planner improvises the DAG" rather than the fixed reference plan.
    """
    llm = get_llm_client()
    plan = decompose_goal(goal, llm)
    print(f"\nGenerated plan for: {goal!r}")
    for t in plan.tasks:
        print(f"  {t.id}: {t.instruction}  (depends_on={t.depends_on})")
    print(f"Execution batches: {plan.execution_batches()}\n")

    outputs = await execute_plan_against_mcp(plan, client, llm)
    for task_id, output in outputs.items():
        print(f"[{task_id}] -> {output}\n")

    print("=" * 60)
    print("FINAL OUTPUT:", final_output(plan, outputs))


async def main():
    print("=" * 60)
    print("Greenfield Planning Agent (decomposition-first)")
    print("=" * 60)

    server_path = os.path.join(PROJECT_ROOT, "mcp_server", "server.py")
    client = MCPClient([sys.executable, server_path])

    try:
        await client.start()
        print("✓ MCP server started")
        print(f"✓ Server capabilities: {client.server_capabilities}")
        print(f"✓ Available tools: {[t['name'] for t in client.tools]}\n")
    except Exception as exc:
        print(f"Failed to start MCP server: {exc}", file=sys.stderr)
        raise

    try:
        mode = input("Run [f]ixed reference plan or [g]enerate from a goal? (f/g): ").strip().lower()
        if mode == "g":
            goal = input("Goal: ").strip() or "Prepare field f1 for a pesticide application"
            await run_llm_generated_plan(client, goal)
        else:
            field_id = input("Field id (default f1): ").strip() or "f1"
            await run_fixed_demo_plan(client, field_id)
    finally:
        print("\nStopping MCP server...")
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
