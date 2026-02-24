"""Category 5: Client Management tools."""

import json
from helpers import _api_get, _api_post, _paginated_get, _format_client, logger


def register(mcp):

    @mcp.tool()
    async def list_clients(console_ip: str = "", site_id: str = "", filter_type: str = "") -> str:
        """List connected clients for a site with optional type filter (WIRED, WIRELESS)."""
        logger.info(f"list_clients for {console_ip} site={site_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        try:
            clients = await _paginated_get(console_ip, f"/sites/{site_id}/clients")
            if filter_type.strip():
                clients = [c for c in clients if c.get("type", "").upper() == filter_type.strip().upper()]
            if not clients:
                return "No clients found"
            lines = [f"Found {len(clients)} client(s):\n"]
            for c in clients:
                lines.append(_format_client(c))
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"list_clients error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def get_client_details(console_ip: str = "", site_id: str = "", client_id: str = "") -> str:
        """Get detailed connection info for a specific client."""
        logger.info(f"get_client_details for {console_ip} client={client_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not client_id.strip():
            return "Error: client_id is required"
        try:
            data = await _api_get(console_ip, f"/sites/{site_id}/clients/{client_id}")
            return f"Client Details:\n  {json.dumps(data, indent=2)}"
        except Exception as e:
            logger.error(f"get_client_details error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def manage_guest_access(console_ip: str = "", site_id: str = "", client_id: str = "", action: str = "") -> str:
        """Authorize or unauthorize a guest client — action must be AUTHORIZE or UNAUTHORIZE."""
        logger.info(f"manage_guest_access for {console_ip} client={client_id} action={action}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not client_id.strip():
            return "Error: client_id is required"
        if action.strip().upper() not in ("AUTHORIZE", "UNAUTHORIZE"):
            return "Error: action must be AUTHORIZE or UNAUTHORIZE"
        try:
            payload = {"action": action.strip().upper()}
            data = await _api_post(console_ip, f"/sites/{site_id}/clients/{client_id}/actions", payload)
            return f"Guest {action.strip().upper()} sent for client {client_id}\n  Response: {json.dumps(data, indent=2)}"
        except Exception as e:
            logger.error(f"manage_guest_access error: {e}")
            return f"Error: {str(e)}"
