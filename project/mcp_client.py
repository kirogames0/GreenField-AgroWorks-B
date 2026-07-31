"""
MCP client. Talks to mcp_server/server.py over stdio.
Real initialize/initialized handshake. Checks server capabilities
before offering risky tools. Tracks tools/list, reacts to
notifications/tools/list_changed by re-fetching. Sends progressToken
correctly under params._meta per spec.
"""

import asyncio
import json
import itertools


class MCPClient:
    def __init__(self, server_cmd):
        self.server_cmd = server_cmd  # e.g. ["python3", "mcp_server/server.py"]
        self.proc = None
        self._id_counter = itertools.count(1)
        self.server_capabilities = {}
        self.tools = []  # last known tools/list result
        self._pending = {}  # request id -> asyncio.Future
        self._reader_task = None

    async def start(self):
        self.proc = await asyncio.create_subprocess_exec(
            *self.server_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )
        self._reader_task = asyncio.create_task(self._read_loop())

        # --- real initialize/initialized handshake ---
        init_result = await self._request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "elicitation": True,   # this client CAN answer elicitation/create
                "sampling": True,      # this client CAN fulfill sampling/createMessage
            },
            "clientInfo": {"name": "greenfield-agent", "version": "0.1.0"},
        })
        self.server_capabilities = init_result.get("capabilities", {})
        await self._notify("initialized", {})

        # Fetch initial tool list now that we're initialized
        await self.refresh_tools()
        return init_result

    def supports(self, capability: str) -> bool:
        """
        Check BEFORE relying on a capability. e.g. don't offer a tool
        that needs elicitation if the server never declared it.
        """
        val = self.server_capabilities.get(capability)
        if isinstance(val, dict):
            return True  # presence of the dict = declared support
        return bool(val)

    async def refresh_tools(self):
        result = await self._request("tools/list", {})
        self.tools = result.get("tools", [])
        return self.tools

    def has_tool(self, name: str) -> bool:
        return any(t["name"] == name for t in self.tools)

    async def call_tool(self, name: str, arguments: dict, progress_token=None, on_progress=None):
        """
        progress_token: if given, passed correctly under params._meta
        per MCP spec (NOT top-level -- that was the bug in the old
        server.py client-side assumption).
        on_progress: optional callback(progress, total) invoked as
        notifications/progress messages arrive tagged with this token.
        """
        params = {"name": name, "arguments": arguments}
        if progress_token is not None:
            params["_meta"] = {"progressToken": progress_token}
            if on_progress is not None:
                self._progress_callbacks = getattr(self, "_progress_callbacks", {})
                self._progress_callbacks[progress_token] = on_progress

        return await self._request("tools/call", params)

    async def _request(self, method: str, params: dict):
        req_id = next(self._id_counter)
        fut = asyncio.get_event_loop().create_future()
        self._pending[req_id] = fut
        msg = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        self.proc.stdin.write((json.dumps(msg) + "\n").encode())
        await self.proc.stdin.drain()
        response = await fut
        if "error" in response:
            raise RuntimeError(f"{method} failed: {response['error']}")
        return response.get("result", {})

    async def _notify(self, method: str, params: dict):
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        self.proc.stdin.write((json.dumps(msg) + "\n").encode())
        await self.proc.stdin.drain()

    async def _read_loop(self):
        while True:
            line = await self.proc.stdout.readline()
            if not line:
                break
            msg = json.loads(line)

            if "id" in msg and msg["id"] in self._pending:
                # response to one of our requests
                self._pending.pop(msg["id"]).set_result(msg)
                continue

            method = msg.get("method")
            if method == "notifications/tools/list_changed":
                # react: re-fetch, don't poll, don't guess.
                # Must NOT await this inline -- refresh_tools() sends a
                # request and awaits its response, but that response
                # can only arrive by going through THIS SAME read loop.
                # Awaiting here would deadlock the loop against itself.
                # Fire it as a background task instead.
                asyncio.create_task(self.refresh_tools())
            elif method == "notifications/progress":
                p = msg.get("params", {})
                token = p.get("progressToken")
                cb = getattr(self, "_progress_callbacks", {}).get(token)
                if cb:
                    cb(p.get("progress"), p.get("total"))

    async def stop(self):
        if self.proc:
            self.proc.stdin.close()
            await self.proc.wait()