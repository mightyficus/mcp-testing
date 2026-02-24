"""Category 7: Hotspot & Firewall tools."""

import json
from helpers import _api_get, _api_post, _api_delete, logger


def register(mcp):

    @mcp.tool()
    async def list_vouchers(console_ip: str = "", site_id: str = "") -> str:
        """List all hotspot vouchers for a site."""
        logger.info(f"list_vouchers for {console_ip} site={site_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        try:
            data = await _api_get(console_ip, f"/sites/{site_id}/hotspot/vouchers")
            vouchers = data.get("data", [])
            if not vouchers:
                return "No vouchers found"
            lines = [f"Found {len(vouchers)} voucher(s):\n"]
            for v in vouchers:
                lines.append(
                    f"  - Code: {v.get('code', 'N/A')} | ID: {v.get('id', 'N/A')} | "
                    f"Duration: {v.get('duration', 'N/A')}min | Used: {v.get('used', 0)}/{v.get('quota', 1)}"
                )
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"list_vouchers error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def create_voucher(console_ip: str = "", site_id: str = "", config_json: str = "") -> str:
        """Create hotspot voucher(s) — provide config as JSON string with count, duration, etc."""
        logger.info(f"create_voucher for {console_ip} site={site_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not config_json.strip():
            return "Error: config_json is required (JSON string with voucher configuration)"
        try:
            payload = json.loads(config_json)
            data = await _api_post(console_ip, f"/sites/{site_id}/hotspot/vouchers", payload)
            return f"Voucher(s) created\n  Response: {json.dumps(data, indent=2)}"
        except json.JSONDecodeError as je:
            return f"Error: Invalid JSON in config_json: {str(je)}"
        except Exception as e:
            logger.error(f"create_voucher error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def delete_voucher(console_ip: str = "", site_id: str = "", voucher_id: str = "") -> str:
        """Delete a hotspot voucher by ID."""
        logger.info(f"delete_voucher for {console_ip} voucher={voucher_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not voucher_id.strip():
            return "Error: voucher_id is required"
        try:
            data = await _api_delete(console_ip, f"/sites/{site_id}/hotspot/vouchers/{voucher_id}")
            return f"Voucher {voucher_id} deleted\n  Response: {json.dumps(data, indent=2)}"
        except Exception as e:
            logger.error(f"delete_voucher error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def list_firewall_policies(console_ip: str = "", site_id: str = "") -> str:
        """List firewall policies and zones for a site."""
        logger.info(f"list_firewall_policies for {console_ip} site={site_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        try:
            policies_data = await _api_get(console_ip, f"/sites/{site_id}/firewall/policies")
            zones_data = await _api_get(console_ip, f"/sites/{site_id}/firewall/zones")
            policies = policies_data.get("data", [])
            zones = zones_data.get("data", [])
            lines = [f"Firewall Overview:\n"]
            lines.append(f"  Policies ({len(policies)}):")
            for p in policies:
                lines.append(
                    f"    - {p.get('name', 'Unnamed')} | ID: {p.get('id', 'N/A')} | "
                    f"Action: {p.get('action', 'N/A')} | Enabled: {p.get('enabled', 'N/A')}"
                )
            lines.append(f"\n  Zones ({len(zones)}):")
            for z in zones:
                lines.append(f"    - {z.get('name', 'Unnamed')} | ID: {z.get('id', 'N/A')}")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"list_firewall_policies error: {e}")
            return f"Error: {str(e)}"
