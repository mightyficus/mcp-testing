"""Category 3: Firmware Operations tools."""

import json
from helpers import _legacy_get, _legacy_post, _paginated_get, _detect_kind, logger


def register(mcp):

    @mcp.tool()
    async def upgrade_device_channel(console_ip: str = "", site_name: str = "default", mac_address: str = "") -> str:
        """Upgrade a device to the current firmware channel release via legacy API."""
        logger.info(f"upgrade_device_channel for {console_ip} mac={mac_address}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not mac_address.strip():
            return "Error: mac_address is required"
        try:
            payload = {"cmd": "upgrade", "mac": mac_address.strip().lower()}
            data = await _legacy_post(console_ip, site_name, "/cmd/devmgr", payload)
            return f"Channel upgrade triggered for {mac_address}\n  Response: {json.dumps(data, indent=2)}"
        except Exception as e:
            logger.error(f"upgrade_device_channel error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def upgrade_device_custom(console_ip: str = "", site_name: str = "default", mac_address: str = "", firmware_url: str = "") -> str:
        """Upgrade a device with a custom firmware URL via legacy API."""
        logger.info(f"upgrade_device_custom for {console_ip} mac={mac_address} url={firmware_url}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not mac_address.strip():
            return "Error: mac_address is required"
        if not firmware_url.strip():
            return "Error: firmware_url is required"
        try:
            payload = {"cmd": "upgrade-external", "mac": mac_address.strip().lower(), "url": firmware_url.strip()}
            data = await _legacy_post(console_ip, site_name, "/cmd/devmgr", payload)
            return f"Custom firmware upgrade triggered for {mac_address}\n  URL: {firmware_url}\n  Response: {json.dumps(data, indent=2)}"
        except Exception as e:
            logger.error(f"upgrade_device_custom error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def change_firmware_channel(console_ip: str = "", site_name: str = "default", channel: str = "") -> str:
        """Change firmware release channel then trigger firmware availability check."""
        logger.info(f"change_firmware_channel for {console_ip} channel={channel}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not channel.strip():
            return "Error: channel is required (e.g., release, rc, beta)"
        try:
            settings_data = await _legacy_get(console_ip, site_name, "/get/setting")
            fw_settings = None
            for section in settings_data.get("data", []):
                if section.get("key") == "super_fwupdate":
                    fw_settings = section
                    break
            if fw_settings is None:
                return "Error: Firmware update settings not found in site settings"
            available = fw_settings.get("available_firmware_channels", [])
            available_lower = [str(c).lower() for c in available]
            if channel.strip().lower() not in available_lower:
                return f"Error: '{channel}' is not a valid channel. Available: {', '.join(str(c) for c in available)}"
            payload = {
                "key": "super_fwupdate",
                "sso_enabled": fw_settings.get("sso_enabled"),
                "controller_channel": fw_settings.get("controller_channel"),
                "firmware_channel": channel.strip(),
                "_id": fw_settings.get("_id"),
            }
            await _legacy_post(console_ip, site_name, "/set/setting/super_fwupdate", payload)
            check_payload = {"cmd": "list-available"}
            await _legacy_post(console_ip, site_name, "/cmd/firmware", check_payload)
            return (
                f"Firmware channel changed to '{channel}'\n"
                f"  Previous available channels: {', '.join(str(c) for c in available)}\n"
                f"  Firmware availability check triggered. Devices may take 30-60s to report new updates."
            )
        except Exception as e:
            logger.error(f"change_firmware_channel error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def check_firmware_updates(console_ip: str = "", site_name: str = "default") -> str:
        """Trigger a firmware availability check for all devices on a site."""
        logger.info(f"check_firmware_updates for {console_ip}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        try:
            payload = {"cmd": "list-available"}
            data = await _legacy_post(console_ip, site_name, "/cmd/firmware", payload)
            return f"Firmware availability check triggered\n  Response: {json.dumps(data, indent=2)}"
        except Exception as e:
            logger.error(f"check_firmware_updates error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def bulk_upgrade_aps(console_ip: str = "", site_id: str = "", site_name: str = "default", firmware_url: str = "") -> str:
        """Bulk upgrade all online APs on a site — channel upgrade or custom URL if provided."""
        logger.info(f"bulk_upgrade_aps for {console_ip} site={site_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        try:
            devices = await _paginated_get(console_ip, f"/sites/{site_id}/devices")
            aps = [d for d in devices if _detect_kind(d) == "ap" and d.get("state") == "ONLINE"]
            if not aps:
                return "No online APs found to upgrade"
            results = []
            for ap in aps:
                mac = ap.get("macAddress", "").lower()
                name = ap.get("name", "Unnamed")
                try:
                    if firmware_url.strip():
                        payload = {"cmd": "upgrade-external", "mac": mac, "url": firmware_url.strip()}
                    else:
                        if not ap.get("firmwareUpdatable", False):
                            results.append(f"  {name} ({mac}): Already up to date")
                            continue
                        payload = {"cmd": "upgrade", "mac": mac}
                    await _legacy_post(console_ip, site_name, "/cmd/devmgr", payload)
                    results.append(f"  {name} ({mac}): Upgrade triggered")
                except Exception as ap_err:
                    results.append(f"  {name} ({mac}): {str(ap_err)}")
            header = f"Bulk AP Upgrade Results ({len(aps)} APs found):\n"
            return header + "\n".join(results)
        except Exception as e:
            logger.error(f"bulk_upgrade_aps error: {e}")
            return f"Error: {str(e)}"
