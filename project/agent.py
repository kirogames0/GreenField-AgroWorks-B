"""
Greenfield AI Agent - connects to MCP server via MCPClient
================================

This agent:
1. Starts the MCP server (Server/server.py) as a subprocess
2. Initializes MCPClient to communicate with it
3. Makes real MCP tool calls (not hardcoded fakes)
4. Respects server capabilities and tool availability
"""

import asyncio
import os
import sys

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
    server_path = os.path.join(script_dir, "Server", "server.py")
    
    # Initialize MCPClient with server command
    client = MCPClient(["python", server_path])
    
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


if __name__ == "__main__":
    asyncio.run(main())
    