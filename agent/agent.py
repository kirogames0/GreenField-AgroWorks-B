"""
Greenfield AI Agent - connects to MCP server via MCPClient
================================

This agent:
1. Starts the MCP server (Server/server.py) as a subprocess
2. Initializes MCPClient to communicate with it
3. Makes real MCP tool calls (not hardcoded fakes)
4. Respects server capabilities and tool availability
"""
from prompts import SYSTEM_PROMPT
import asyncio
import os
import sys
import json
from mcp_client import MCPClient
from safety import is_restricted
from tools import (
    check_inventory,
    check_crop_status,
    request_human_approval,
    authenticate_worker,
    generate_compliance_report,
)


async def process_request(user_request, client):
    """Process a user request by calling appropriate MCP tools on the server."""
    restricted, chemical = is_restricted(user_request)

    if restricted:
        return (
            f"⛔ STOP\n"
            f"{chemical} is a restricted chemical.\n"
            f"{await request_human_approval(client)}"
        )

    request = user_request.lower()

    if "inventory" in request:
        return await check_inventory(client)

    if "crop" in request or "field" in request:
        # Try to extract field_id if specified
        field_id = None
        if "field" in request:
            # Simple extraction: look for 'f1', 'f2', etc.
            parts = request.split()
            for part in parts:
                if part.startswith('f') and part[1:].isdigit():
                    field_id = part
                    break
        return await check_crop_status(client, field_id)
    
    if "worker" in request or "authenticate" in request:
        # Try to extract worker_id if specified
        worker_id = None
        parts = request.split()
        for part in parts:
            if part.startswith('w') and part[1:].isdigit():
                worker_id = part
                break
        return await authenticate_worker(client, worker_id)
    
    if "compliance" in request or "report" in request:
        # For now, return a message indicating this needs parameters
        return "To generate a compliance report, please provide: buyer_id, start_date (YYYY-MM-DD), and end_date (YYYY-MM-DD)"

    return "I don't understand your request. Try asking about inventory, crop status, worker authentication, or compliance reports."


async def main():
    """Main agent loop."""
    print("=" * 60)
    print("🌱 Greenfield AI Assistant")
    print("=" * 60)
    print("\nStarting MCP server...")
    
    # Get the Server directory path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    server_path = os.path.join(project_root, "mcp_server", "server.py")
    
    # Initialize MCPClient with server command using full Python executable path
    python_executable = sys.executable
    client = MCPClient([python_executable, server_path])
    
    try:
        # Start the server and complete handshake
        await client.start()
        print(f"✓ MCP server started and initialized")
        print(f"✓ Server capabilities: {client.server_capabilities}")
        print(f"✓ Available tools: {[t['name'] for t in client.tools]}\n")
    except Exception as e:
        print(f"✗ Failed to start MCP server: {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        while True:
            user_request = input("\nEnter your request (or 'quit' to exit): ").strip()
            
            if user_request.lower() in ("quit", "exit", "q"):
                break
            
            if not user_request:
                continue
            
            print("\nAssistant:", end=" ")
            response = await process_request(user_request, client)
            print(response)
    
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    
    finally:
        # Clean up: stop the server
        print("\nStopping MCP server...", file=sys.stderr)
        await client.stop()

class AgroWorksAgent:
    def __init__(self):
        # 1. Connect to the existing MCP Server (reusing mcp_server/)
        self.mcp = MCPClient(server_url="http://localhost:8000") 
        
        # 2. Initialize Short-Term Buffer
        self.short_term_buffer = []
        self.buffer_limit = 5

    def process_message(self, user_input: str) -> str:
        """Main live loop for the agent."""
        
        # A. RAG Pipeline: Check knowledge base before answering
        # The agent queries the MCP server's RAG tool for context
        rag_context = self.mcp.call_tool("keyword_search", {"query": user_input})
        
        # B. Retrieve Long-Term Memory
        # Fetch relevant past session data from the DB via MCP
        user_memory = self.mcp.call_tool("fetch_long_term_memory", {"query": user_input})

        # C. Construct the Augmented Prompt
        context_injected_prompt = f"""
        {SYSTEM_PROMPT}
        
        Relevant Knowledge Base Info: {rag_context}
        Relevant Past User Memory: {user_memory}
        
        User: {user_input}
        """

        # D. Generate Response (using your LLM integration)
        response = self._generate_llm_response(context_injected_prompt, self.short_term_buffer)

        # E. Update Short-Term Buffer
        self.short_term_buffer.append({"role": "user", "content": user_input})
        self.short_term_buffer.append({"role": "assistant", "content": response})

        # F. Memory Lifecycle Trigger: Promote-or-Drop & Consolidation
        if len(self.short_term_buffer) >= self.buffer_limit:
            self._trigger_memory_consolidation()

        return response

    def _trigger_memory_consolidation(self):
        """Evaluates the short-term buffer and persists valuable facts to the DB."""
        conversation_dump = json.dumps(self.short_term_buffer)
        
        # 1. Promote-or-Drop: Ask the LLM if there are durable facts to remember
        extraction = self._generate_llm_response(
            f"{PROMOTE_OR_DROP_PROMPT}\nConversation: {conversation_dump}"
        )
        
        if "NO_NEW_FACTS" not in extraction:
            # 2. Consolidation: Write to DB via the existing MCP server tool
            self.mcp.call_tool("store_long_term_memory", {"fact": extraction})
            
        # 3. Clear/Slide the short-term buffer
        self.short_term_buffer = self.short_term_buffer[-2:] # Keep last turn for context
if __name__ == "__main__":
    asyncio.run(main())
    