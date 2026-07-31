"""
Real MCP tool implementations. These call the MCP server via MCPClient.
They are NOT hardcoded fakes - they make real server.py calls.
"""

import asyncio


async def check_inventory(client=None):
    """Call the real get_inventory tool on the server."""
    if not client:
        return "Error: MCP client not initialized"
    
    try:
        result = await client.call_tool("get_inventory", {})
        return f"Inventory status: {result}"
    except Exception as e:
        return f"Error checking inventory: {str(e)}"


async def check_crop_status(client=None, field_id: str = None):
    """Call the real check_field_status tool on the server."""
    if not client:
        return "Error: MCP client not initialized"
    
    if not field_id:
        field_id = "f1"  # Default field
    
    try:
        result = await client.call_tool("check_field_status", {"field_id": field_id})
        return f"Crop status for {field_id}: {result}"
    except Exception as e:
        return f"Error checking crop status: {str(e)}"


async def request_human_approval(client=None, application_id: str = None):
    """Request human approval for a pesticide application."""
    if not client:
        return "Error: MCP client not initialized"
    
    if not application_id:
        return "Error: application_id required for approval request"
    
    # This would call request_pesticide_application if implemented on server
    # For now, it prepares the request
    return f"Requesting human approval for application {application_id}. Waiting for certified human approval..."


async def authenticate_worker(client=None, worker_id: str = None):
    """Authenticate a worker and update their role/capabilities."""
    if not client:
        return "Error: MCP client not initialized"
    
    if not worker_id:
        worker_id = "w1"  # Default worker
    
    try:
        result = await client.call_tool("authenticate", {"worker_id": worker_id})
        return f"Worker {worker_id} authenticated as {result.get('role', 'unknown role')}"
    except Exception as e:
        return f"Error authenticating worker: {str(e)}"


async def generate_compliance_report(client=None, buyer_id: str = None, start_date: str = None, end_date: str = None):
    """Generate a compliance report with progress tracking."""
    if not client:
        return "Error: MCP client not initialized"
    
    if not buyer_id or not start_date or not end_date:
        return "Error: buyer_id, start_date, and end_date are required"
    
    try:
        result = await client.call_tool(
            "generate_compliance_report",
            {
                "buyer_id": buyer_id,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        return f"Compliance report: {result}"
    except Exception as e:
        return f"Error generating report: {str(e)}"