"""
Greenfield AI Agent — session-aware agent loop with RAG and episodic memory.
This agent starts the existing MCP server, calls real MCP tools, stores
episodic buffer promotions, and uses Mistral for generative answers.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from prompts import SYSTEM_PROMPT
from mcp_client import MCPClient
from mistral_client import MistralClient
from memory.scratchpad import Scratchpad
from memory.short_term_buffer import ShortTermBuffer
from mcp_server.rag.self_rag_check import (
    validate_retrieval_and_answer,
    validate_memory_recall_output,
)


class AgroWorksAgent:
    def __init__(self, client: MCPClient, buffer_limit: int = 20):
        self.client = client
        self.buffer_limit = buffer_limit
        self.scratchpads: dict[str, Scratchpad] = {}
        self.buffers: dict[str, ShortTermBuffer] = {}
        self.llm = MistralClient()

    def get_scratchpad(self, session_id: str) -> Scratchpad:
        if session_id not in self.scratchpads:
            self.scratchpads[session_id] = Scratchpad()
        return self.scratchpads[session_id]

    def get_buffer(self, session_id: str) -> ShortTermBuffer:
        if session_id not in self.buffers:
            self.buffers[session_id] = ShortTermBuffer(max_messages=self.buffer_limit)
        return self.buffers[session_id]

    async def process_message(self, session_id: str, user_input: str) -> str:
        scratchpad = self.get_scratchpad(session_id)
        buffer = self.get_buffer(session_id)

        buffer.add("user", user_input)
        await self._persist_overflow_promotions(session_id, buffer.take_new_overflow_decisions())

        self._update_scratchpad_for_input(scratchpad, user_input)

        rag_result = await self._call_rag_tool(user_input)
        memory_result = await self._fetch_episodic_memory(session_id, user_input)

        response, tokens_used = self._generate_response(
            session_id=session_id,
            user_input=user_input,
            scratchpad=scratchpad,
            buffer=buffer,
            rag_result=rag_result,
            memory_result=memory_result,
        )

        buffer.add("assistant", response)
        return response

    def _update_scratchpad_for_input(self, scratchpad: Scratchpad, user_input: str) -> None:
        lower = user_input.lower()

        if "compliance report" in lower or "generate compliance report" in lower:
            scratchpad.set_task(
                "generate compliance report",
                "gather buyer/date range and call generate_compliance_report tool",
            )
        elif "authenticate" in lower or "worker" in lower:
            scratchpad.set_task(
                "authenticate worker",
                "verify worker credentials and refresh session role",
            )
        elif "inventory" in lower:
            scratchpad.set_task(
                "inventory check",
                "retrieve current inventory levels for requested chemicals",
            )
        elif "field" in lower or "crop" in lower:
            scratchpad.set_task(
                "field status lookup",
                "use check_field_status to answer crop or field questions",
            )

    async def _persist_overflow_promotions(self, session_id: str, decisions: list[dict]) -> None:
        for decision in decisions:
            if decision["action"] != "promote_to_episodic":
                continue

            item = decision["item"]
            content = item.content if hasattr(item, "content") else str(item)
            await self.client.call_tool(
                "store_episodic_memory",
                {
                    "session_id": session_id,
                    "role": "assistant",
                    "content": content,
                    "source": "buffer_overflow",
                    "created_at": datetime.utcnow().date().isoformat(),
                },
            )

    async def _call_rag_tool(self, query: str) -> dict[str, Any]:
        if not self.client.has_tool("search_knowledge_base"):
            return {"results": [], "validation": None, "architecture_used": "none"}

        result = await self.client.call_tool("search_knowledge_base", {"query": query, "top_k": 3})
        if result.get("results"):
            return result

        # fallback to a deeper reasoning search if the simple retrieval returns nothing
        if self.client.has_tool("deep_research_knowledge_base"):
            return await self.client.call_tool(
                "deep_research_knowledge_base",
                {"query": query, "top_k": 3},
            )
        return result

    async def _fetch_episodic_memory(self, session_id: str, query: str) -> dict[str, Any]:
        if not self.client.has_tool("fetch_episodic_memory"):
            return {"memories": []}

        return await self.client.call_tool(
            "fetch_episodic_memory",
            {"session_id": session_id, "query": query, "limit": 5},
        )

    def _compose_prompt(
        self,
        user_input: str,
        scratchpad: Scratchpad,
        buffer: ShortTermBuffer,
        rag_result: dict[str, Any],
        memory_result: dict[str, Any],
    ) -> str:
        sections = [SYSTEM_PROMPT.strip()]

        if scratchpad.current_plan:
            sections.append(f"Current plan: {scratchpad.current_plan}")
        if scratchpad.sub_goal:
            sections.append(f"Sub-goal: {scratchpad.sub_goal}")
        if scratchpad.working_state:
            sections.append(f"Working state: {json.dumps(scratchpad.working_state)}")

        if rag_result.get("results"):
            rag_texts = [str(item.get("text", item.get("payload", ""))) for item in rag_result["results"]]
            sections.append("Relevant knowledge base snippets:")
            sections.extend(rag_texts)

        if memory_result.get("memories"):
            sections.append("Relevant episodic memory:")
            sections.extend([m["content"] for m in memory_result["memories"]])

        transcript = buffer.as_transcript()
        if transcript:
            sections.append("Recent conversation transcript:")
            sections.append(transcript)

        sections.append(f"User: {user_input}")
        return "\n\n".join(sections)

    def _generate_response(
        self,
        session_id: str,
        user_input: str,
        scratchpad: Scratchpad,
        buffer: ShortTermBuffer,
        rag_result: dict[str, Any],
        memory_result: dict[str, Any],
    ) -> tuple[str, int]:
        prompt = self._compose_prompt(
            user_input=user_input,
            scratchpad=scratchpad,
            buffer=buffer,
            rag_result=rag_result,
            memory_result=memory_result,
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": prompt},
        ]

        answer, tokens_used = self.llm.chat(messages=messages, temperature=0.0, max_tokens=512)

        rag_contexts = [
            str(item.get("text", item.get("payload", "")))
            for item in rag_result.get("results", [])
        ]
        memory_contexts = [item.get("content", "") for item in memory_result.get("memories", [])]

        rag_validation = validate_retrieval_and_answer(
            query=user_input,
            retrieved_contexts=rag_contexts,
            generated_answer=answer,
            source="RAG",
        ) if rag_contexts else {"passed": True, "trace": []}

        memory_validation = validate_memory_recall_output(
            query=user_input,
            recalled_memories=memory_contexts,
            generated_answer=answer,
            source="memory-recall",
        ) if memory_contexts else {"passed": True, "trace": []}

        if not rag_validation["passed"] or not memory_validation["passed"]:
            trace = rag_validation["trace"] + memory_validation["trace"]
            return (
                "I cannot answer confidently because retrieved supporting content failed validation. "
                "Please ask again or provide a simpler question.\n"
                "Validation trace:\n" + "\n".join(trace),
                tokens_used,
            )

        return answer, tokens_used


async def main():
    print("=" * 60)
    print("🌱 Greenfield AI Assistant")
    print("=" * 60)
    print("Starting MCP server and connecting agent...\n")

    server_path = os.path.join(PROJECT_ROOT, "mcp_server", "server.py")
    python_executable = sys.executable
    client = MCPClient([python_executable, server_path])

    try:
        await client.start()
        print("✓ MCP server started")
        print(f"✓ Server capabilities: {client.server_capabilities}")
        print(f"✓ Available tools: {[tool['name'] for tool in client.tools]}\n")
    except Exception as exc:
        print(f"Failed to start MCP server: {exc}", file=sys.stderr)
        raise

    agent = AgroWorksAgent(client=client, buffer_limit=20)
    session_id = input("Session ID (use the same ID across runs to preserve memory): ").strip() or "default"

    try:
        while True:
            user_input = input("\nEnter request (or 'quit'): ").strip()
            if user_input.lower() in {"quit", "exit", "q"}:
                break
            if not user_input:
                continue

            response = await agent.process_message(session_id, user_input)
            print("\nAssistant:")
            print(response)

    except KeyboardInterrupt:
        print("\nSession ended.")

    finally:
        print("\nStopping MCP server...")
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())

    