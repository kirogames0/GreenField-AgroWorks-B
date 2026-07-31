"""
Greenfield Agroworks MCP Server - HTTP Transport Version
=========================================================

This is an alternative to server.py that uses HTTP transport instead of stdio.
Same MCP protocol, same capabilities, different transport layer.

This version can be run as:
    python server_http.py
    
And will start an HTTP server on http://localhost:8000/mcp

The client would connect via HTTP with POST requests to /mcp endpoint.
Each request is a JSON-RPC message in the body.
"""

import asyncio
import json
import sqlite3
import sys
import os
from typing import Callable
from dataclasses import dataclass

# Import all the same handlers and tools from the stdio version
from server import (
    _initialize_database_if_needed,
    handle_initialize,
    handle_tools_list,
    handle_tools_call,
    handle_resources_list,
    handle_resources_read,
    handle_prompts_list,
    handle_elicitation_create,
    handle_sampling_createMessage,
    Session,
    DB_PATH,
    get_db_cursor,
)


# Get the project root directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_DIR = os.path.join(PROJECT_ROOT, "DB")


# HTTP server using asyncio (minimal implementation without external libraries)
class HTTPMCPServer:
    """Simple HTTP MCP server using asyncio."""
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self.sessions = {}  # Map connection IDs to session state
        self.next_session_id = 1
    
    async def start(self):
        """Start the HTTP server."""
        # Initialize database
        _initialize_database_if_needed()
        
        print(f"Starting HTTP MCP Server on http://{self.host}:{self.port}/mcp", file=sys.stderr)
        print(f"Database: {DB_PATH}", file=sys.stderr)
        
        # Create and start server
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        
        async with server:
            await server.serve_forever()
    
    async def handle_client(self, reader, writer):
        """Handle an HTTP connection."""
        addr = writer.get_extra_info('peername')
        print(f"Client connected: {addr}", file=sys.stderr)
        
        session_id = self.next_session_id
        self.next_session_id += 1
        self.sessions[session_id] = Session()
        
        try:
            while True:
                # Read HTTP request line
                line = await reader.readline()
                if not line:
                    break
                
                request_line = line.decode().strip()
                if not request_line:
                    continue
                
                # Parse HTTP request (simplified for POST requests)
                if request_line.startswith("POST"):
                    # Read headers
                    content_length = 0
                    while True:
                        header = await reader.readline()
                        if not header or header == b"\r\n":
                            break
                        header_str = header.decode().strip().lower()
                        if header_str.startswith("content-length:"):
                            content_length = int(header_str.split(":")[1].strip())
                    
                    # Read body
                    if content_length > 0:
                        body = await reader.readexactly(content_length)
                        try:
                            request = json.loads(body.decode())
                            
                            # Process MCP request
                            response = await self.process_mcp_request(
                                request, 
                                session_id,
                                lambda msg: None  # notifications would be sent back in response
                            )
                            
                            # Send HTTP response
                            response_json = json.dumps(response)
                            response_body = response_json.encode()
                            
                            http_response = (
                                "HTTP/1.1 200 OK\r\n"
                                f"Content-Length: {len(response_body)}\r\n"
                                "Content-Type: application/json\r\n"
                                "Connection: keep-alive\r\n"
                                "\r\n"
                            ).encode() + response_body
                            
                            writer.write(http_response)
                            await writer.drain()
                        
                        except json.JSONDecodeError:
                            # Send error response
                            error_response = json.dumps({
                                "jsonrpc": "2.0",
                                "error": {"code": -32700, "message": "Parse error"}
                            }).encode()
                            
                            http_response = (
                                "HTTP/1.1 400 Bad Request\r\n"
                                f"Content-Length: {len(error_response)}\r\n"
                                "Content-Type: application/json\r\n"
                                "\r\n"
                            ).encode() + error_response
                            
                            writer.write(http_response)
                            await writer.drain()
                else:
                    # Send 405 for non-POST requests
                    http_response = (
                        "HTTP/1.1 405 Method Not Allowed\r\n"
                        "Content-Length: 0\r\n"
                        "\r\n"
                    ).encode()
                    writer.write(http_response)
                    await writer.drain()
        
        except asyncio.IncompleteReadError:
            pass
        except Exception as e:
            print(f"Error handling client: {e}", file=sys.stderr)
        
        finally:
            # Clean up session
            if session_id in self.sessions:
                del self.sessions[session_id]
            writer.close()
            await writer.wait_closed()
            print(f"Client disconnected: {addr}", file=sys.stderr)
    
    async def process_mcp_request(
        self,
        request: dict,
        session_id: int,
        send_notification: Callable,
    ) -> dict:
        """Process an MCP request and return response."""
        session = self.sessions[session_id]
        method = request.get("method")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            if method == "initialize":
                return handle_initialize(request)
            
            elif method == "initialized":
                session.initialized = True
                return {}  # No response to notification
            
            elif method == "tools/list":
                if not session.initialized:
                    return {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {"code": -32002, "message": "Server not initialized"}
                    }
                return {"jsonrpc": "2.0", "id": request.get("id"), "result": handle_tools_list(session)}
            
            elif method == "tools/call":
                if not session.initialized:
                    return {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {"code": -32002, "message": "Server not initialized"}
                    }
                return await handle_tools_call(request, session, cursor, send_notification)
            
            elif method == "resources/list":
                try:
                    result = handle_resources_list(cursor)
                    return {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
                except Exception as e:
                    return {"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": -32603, "message": str(e)}}
            
            elif method == "resources/read":
                try:
                    uri = request.get("params", {}).get("uri")
                    if not uri:
                        return {"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": -32602, "message": "Missing uri parameter"}}
                    result = handle_resources_read(uri, cursor)
                    return {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
                except Exception as e:
                    return {"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": -32603, "message": str(e)}}
            
            elif method == "prompts/list":
                try:
                    result = handle_prompts_list()
                    return {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
                except Exception as e:
                    return {"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": -32603, "message": str(e)}}
            
            elif method == "elicitation/create":
                return await handle_elicitation_create(request, send_notification)
            
            elif method == "sampling/createMessage":
                return await handle_sampling_createMessage(request, send_notification)
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {"code": -32601, "message": f"Unknown method {method}"}
                }
        
        finally:
            conn.close()


async def main():
    """Start the HTTP server."""
    server = HTTPMCPServer(host="0.0.0.0", port=8000)
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped", file=sys.stderr)
