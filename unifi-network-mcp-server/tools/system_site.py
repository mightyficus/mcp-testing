"""Category 1: System & Site Info tools."""

import json
from helpers import _api_get, _legacy_get, logger


def register(mcp):

    @mcp.tool()
    async def get_app_info(console_ip: str = "") -> str:
        """Get UniFi Console application info including version."""
        logger.info(f"get_app_info for {console_ip}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        try:
            data = await _api_get(console_ip, "/info")
            return (
                f"Console Info:\n"
                f"  Version: {data.get('version', 'N/A')}\n"
                f"  Name: {data.get('name', 'N/A')}\n"
                f"  Hostname: {data.get('hostname', 'N/A')}\n"
                f"  Raw: {json.dumps(data, indent=2)}"
            )
        except Exception as e:
            logger.error(f"get_app_info error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def list_sites(console_ip: str = "") -> str:
        """List all UniFi sites with their IDs and names."""
        logger.info(f"list_sites for {console_ip}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        try:
            data = await _api_get(console_ip, "/sites")
            sites = data.get("data", [])
            if not sites:
                return "No sites found"
            lines = [f"Found {len(sites)} site(s):\n"]
            for s in sites:
                lines.append(
                    f"  - {s.get('name', 'Unnamed')} | ID: {s.get('id', 'N/A')} | "
                    f"Ref: {s.get('internalReference', 'N/A')}"
                )
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"list_sites error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def get_site_settings(console_ip: str = "", site_name: str = "default") -> str:
        """Fetch site settings including firmware channel via legacy API."""
        logger.info(f"get_site_settings for {console_ip} site={site_name}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        try:
            data = await _legacy_get(console_ip, site_name, "/get/setting")
            settings = data.get("data", [])
            lines = [f"Site settings for '{site_name}' ({len(settings)} sections):\n"]
            for section in settings:
                key = section.get("key", "unknown")
                if key == "super_fwupdate":
                    channels = section.get("available_firmware_channels", [])
                    current = section.get("firmware_channel", "N/A")
                    lines.append(f"  Firmware Channel: {current}")
                    lines.append(f"  Available Channels: {', '.join(str(c) for c in channels)}")
                    lines.append(f"  SSO Enabled: {section.get('sso_enabled', 'N/A')}")
                    lines.append(f"  Controller Channel: {section.get('controller_channel', 'N/A')}")
                    lines.append(f"  FW Update ID: {section.get('_id', 'N/A')}")
                else:
                    lines.append(f"  [{key}]")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"get_site_settings error: {e}")
            return f"Error: {str(e)}"
