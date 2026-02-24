"""Category 6: Network Management tools."""

import json
from helpers import _api_get, _api_post, _api_put, _api_delete, logger


def register(mcp):

    @mcp.tool()
    async def list_networks(console_ip: str = "", site_id: str = "") -> str:
        """List all networks (VLANs) for a site."""
        logger.info(f"list_networks for {console_ip} site={site_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        try:
            data = await _api_get(console_ip, f"/sites/{site_id}/networks")
            networks = data.get("data", [])
            if not networks:
                return "No networks found"
            lines = [f"Found {len(networks)} network(s):\n"]
            for n in networks:
                lines.append(
                    f"  - {n.get('name', 'Unnamed')} | ID: {n.get('id', 'N/A')} | "
                    f"VLAN: {n.get('vlan', 'N/A')} | Subnet: {n.get('subnet', 'N/A')} | "
                    f"Purpose: {n.get('purpose', 'N/A')}"
                )
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"list_networks error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def create_network(console_ip: str = "", site_id: str = "", config_json: str = "") -> str:
        """Create a new network (VLAN) — provide config as JSON string."""
        logger.info(f"create_network for {console_ip} site={site_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not config_json.strip():
            return "Error: config_json is required (JSON string with network configuration)"
        try:
            payload = json.loads(config_json)
            data = await _api_post(console_ip, f"/sites/{site_id}/networks", payload)
            return f"Network created\n  Response: {json.dumps(data, indent=2)}"
        except json.JSONDecodeError as je:
            return f"Error: Invalid JSON in config_json: {str(je)}"
        except Exception as e:
            logger.error(f"create_network error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def update_network(console_ip: str = "", site_id: str = "", network_id: str = "", config_json: str = "") -> str:
        """Update an existing network (VLAN) — provide config as JSON string."""
        logger.info(f"update_network for {console_ip} network={network_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not network_id.strip():
            return "Error: network_id is required"
        if not config_json.strip():
            return "Error: config_json is required (JSON string with updated network configuration)"
        try:
            payload = json.loads(config_json)
            data = await _api_put(console_ip, f"/sites/{site_id}/networks/{network_id}", payload)
            return f"Network {network_id} updated\n  Response: {json.dumps(data, indent=2)}"
        except json.JSONDecodeError as je:
            return f"Error: Invalid JSON in config_json: {str(je)}"
        except Exception as e:
            logger.error(f"update_network error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def delete_network(console_ip: str = "", site_id: str = "", network_id: str = "") -> str:
        """Delete a network (VLAN) by ID."""
        logger.info(f"delete_network for {console_ip} network={network_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not network_id.strip():
            return "Error: network_id is required"
        try:
            data = await _api_delete(console_ip, f"/sites/{site_id}/networks/{network_id}")
            return f"Network {network_id} deleted\n  Response: {json.dumps(data, indent=2)}"
        except Exception as e:
            logger.error(f"delete_network error: {e}")
            return f"Error: {str(e)}"
