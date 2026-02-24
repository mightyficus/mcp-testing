"""Category 4: WiFi Broadcasts tools."""

import json
from helpers import _api_get, _api_post, _api_put, _api_delete, logger


def register(mcp):

    @mcp.tool()
    async def list_wifi_broadcasts(console_ip: str = "", site_id: str = "") -> str:
        """List all WiFi SSIDs (broadcasts) for a site."""
        logger.info(f"list_wifi_broadcasts for {console_ip} site={site_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        try:
            data = await _api_get(console_ip, f"/sites/{site_id}/wifi/broadcasts")
            broadcasts = data.get("data", [])
            if not broadcasts:
                return "No WiFi broadcasts found"
            lines = [f"Found {len(broadcasts)} WiFi broadcast(s):\n"]
            for b in broadcasts:
                enabled = "Enabled" if b.get("enabled", False) else "Disabled"
                lines.append(
                    f"  {enabled} {b.get('name', 'Unnamed')} | ID: {b.get('id', 'N/A')} | "
                    f"Security: {b.get('security', 'N/A')} | Band: {b.get('band', 'N/A')}"
                )
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"list_wifi_broadcasts error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def get_wifi_broadcast(console_ip: str = "", site_id: str = "", broadcast_id: str = "") -> str:
        """Get details of a specific WiFi SSID broadcast."""
        logger.info(f"get_wifi_broadcast for {console_ip} broadcast={broadcast_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not broadcast_id.strip():
            return "Error: broadcast_id is required"
        try:
            data = await _api_get(console_ip, f"/sites/{site_id}/wifi/broadcasts/{broadcast_id}")
            return f"WiFi Broadcast Details:\n  {json.dumps(data, indent=2)}"
        except Exception as e:
            logger.error(f"get_wifi_broadcast error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def create_wifi_broadcast(console_ip: str = "", site_id: str = "", config_json: str = "") -> str:
        """Create a new WiFi SSID broadcast — provide config as JSON string."""
        logger.info(f"create_wifi_broadcast for {console_ip} site={site_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not config_json.strip():
            return "Error: config_json is required (JSON string with SSID configuration)"
        try:
            payload = json.loads(config_json)
            data = await _api_post(console_ip, f"/sites/{site_id}/wifi/broadcasts", payload)
            return f"WiFi broadcast created\n  Response: {json.dumps(data, indent=2)}"
        except json.JSONDecodeError as je:
            return f"Error: Invalid JSON in config_json: {str(je)}"
        except Exception as e:
            logger.error(f"create_wifi_broadcast error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def update_wifi_broadcast(console_ip: str = "", site_id: str = "", broadcast_id: str = "", config_json: str = "") -> str:
        """Update an existing WiFi SSID broadcast — provide config as JSON string."""
        logger.info(f"update_wifi_broadcast for {console_ip} broadcast={broadcast_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not broadcast_id.strip():
            return "Error: broadcast_id is required"
        if not config_json.strip():
            return "Error: config_json is required (JSON string with updated SSID configuration)"
        try:
            payload = json.loads(config_json)
            data = await _api_put(console_ip, f"/sites/{site_id}/wifi/broadcasts/{broadcast_id}", payload)
            return f"WiFi broadcast {broadcast_id} updated\n  Response: {json.dumps(data, indent=2)}"
        except json.JSONDecodeError as je:
            return f"Error: Invalid JSON in config_json: {str(je)}"
        except Exception as e:
            logger.error(f"update_wifi_broadcast error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def delete_wifi_broadcast(console_ip: str = "", site_id: str = "", broadcast_id: str = "") -> str:
        """Delete a WiFi SSID broadcast by ID."""
        logger.info(f"delete_wifi_broadcast for {console_ip} broadcast={broadcast_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not broadcast_id.strip():
            return "Error: broadcast_id is required"
        try:
            data = await _api_delete(console_ip, f"/sites/{site_id}/wifi/broadcasts/{broadcast_id}")
            return f"WiFi broadcast {broadcast_id} deleted\n  Response: {json.dumps(data, indent=2)}"
        except Exception as e:
            logger.error(f"delete_wifi_broadcast error: {e}")
            return f"Error: {str(e)}"
