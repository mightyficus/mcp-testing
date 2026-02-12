#!/usr/bin/env python3
"""Simple UniFi Network MCP Server - Manage UniFi devices, firmware, WiFi, and networks via MCP."""

import os
import sys
import json
import logging
from datetime import datetime, timezone

import httpx
from mcp.server.fastmcp import FastMCP

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("unifi-network-server")

# Initialize MCP server - NO PROMPT PARAMETER
mcp = FastMCP("unifi-network")

# === CONFIGURATION ===

REPORTS_DIR = "/reports"


# === INTERNAL HELPERS (not tools) ===

def _get_headers() -> dict:
    api_key = os.environ.get("UNIFI_API_KEY", "")
    if not api_key.strip():
        raise ValueError("UNIFI_API_KEY environment variable is not set")
    return {"Content-Type": "application/json;charset=UTF-8", "X-API-KEY": api_key}


def _api_url(console_ip: str, path: str) -> str:
    return f"https://{console_ip}/proxy/network/integration/v1{path}"


def _legacy_url(console_ip: str, site_name: str, path: str) -> str:
    return f"https://{console_ip}/proxy/network/api/s/{site_name}{path}"


async def _api_get(console_ip: str, path: str) -> dict:
    url = _api_url(console_ip, path)
    headers = _get_headers()
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json() if response.content else {}


async def _api_post(console_ip: str, path: str, payload: dict) -> dict:
    url = _api_url(console_ip, path)
    headers = _get_headers()
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        return response.json() if response.content else {}


async def _api_put(console_ip: str, path: str, payload: dict) -> dict:
    url = _api_url(console_ip, path)
    headers = _get_headers()
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.put(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        return response.json() if response.content else {}


async def _api_delete(console_ip: str, path: str) -> dict:
    url = _api_url(console_ip, path)
    headers = _get_headers()
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.delete(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json() if response.content else {}


async def _legacy_get(console_ip: str, site_name: str, path: str) -> dict:
    url = _legacy_url(console_ip, site_name, path)
    headers = _get_headers()
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json() if response.content else {}


async def _legacy_post(console_ip: str, site_name: str, path: str, payload: dict) -> dict:
    url = _legacy_url(console_ip, site_name, path)
    headers = _get_headers()
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        return response.json() if response.content else {}


async def _paginated_get(console_ip: str, path: str) -> list:
    """Fetch all pages from a paginated Integration API endpoint."""
    headers = _get_headers()
    all_data = []
    async with httpx.AsyncClient(verify=False) as client:
        # First call to get total count
        url = _api_url(console_ip, path)
        response = await client.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        body = response.json() if response.content else {}
        total = int(body.get("totalCount", 0))
        all_data.extend(body.get("data", []))
        # Paginate in chunks of 200
        page_size = 200
        fetched = len(all_data)
        while fetched < total:
            limit = min(page_size, total - fetched)
            sep = "&" if "?" in path else "?"
            page_url = _api_url(console_ip, f"{path}{sep}limit={limit}&offset={fetched}")
            resp = await client.get(page_url, headers=headers, timeout=15)
            resp.raise_for_status()
            page_body = resp.json() if resp.content else {}
            data = page_body.get("data", [])
            if not data:
                break
            all_data.extend(data)
            fetched += len(data)
    return all_data


def _format_device(device: dict) -> str:
    name = device.get("name", "Unnamed")
    mac = device.get("macAddress", "N/A")
    model = device.get("model", "N/A")
    state = device.get("state", "UNKNOWN")
    fw = device.get("firmwareVersion", "N/A")
    ip = device.get("ipAddress", "N/A")
    did = device.get("id", "N/A")
    updatable = device.get("firmwareUpdatable", False)
    features = ", ".join(device.get("features", []))
    return (
        f"  Name: {name}\n"
        f"  ID: {did}\n"
        f"  MAC: {mac}\n"
        f"  Model: {model}\n"
        f"  IP: {ip}\n"
        f"  State: {state}\n"
        f"  Firmware: {fw}\n"
        f"  Updatable: {updatable}\n"
        f"  Features: {features}"
    )


def _format_client(client: dict) -> str:
    name = client.get("name", client.get("hostname", "Unknown"))
    mac = client.get("macAddress", "N/A")
    ip = client.get("ipAddress", "N/A")
    conn_type = client.get("type", "N/A")
    return f"  Name: {name} | MAC: {mac} | IP: {ip} | Type: {conn_type}"


def _detect_kind(device: dict) -> str:
    features = device.get("features", []) or []
    if "accessPoint" in features:
        if "switching" not in features:
            return "ap"
        interfaces = device.get("interfaces", {})
        if interfaces.get("radios"):
            return "ap"
    if "switching" in features:
        return "switch"
    return "unknown"


def _write_report(filename: str, content: str) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w") as f:
        f.write(content)
    return filepath


# === CATEGORY 1: SYSTEM & SITE INFO ===

@mcp.tool()
async def get_app_info(console_ip: str = "") -> str:
    """Get UniFi Console application info including version."""
    logger.info(f"get_app_info for {console_ip}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    try:
        data = await _api_get(console_ip, "/info")
        return (
            f"✅ Console Info:\n"
            f"  Version: {data.get('version', 'N/A')}\n"
            f"  Name: {data.get('name', 'N/A')}\n"
            f"  Hostname: {data.get('hostname', 'N/A')}\n"
            f"  Raw: {json.dumps(data, indent=2)}"
        )
    except Exception as e:
        logger.error(f"get_app_info error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def list_sites(console_ip: str = "") -> str:
    """List all UniFi sites with their IDs and names."""
    logger.info(f"list_sites for {console_ip}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    try:
        data = await _api_get(console_ip, "/sites")
        sites = data.get("data", [])
        if not sites:
            return "⚠️ No sites found"
        lines = [f"✅ Found {len(sites)} site(s):\n"]
        for s in sites:
            lines.append(
                f"  - {s.get('name', 'Unnamed')} | ID: {s.get('id', 'N/A')} | "
                f"Ref: {s.get('internalReference', 'N/A')}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"list_sites error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def get_site_settings(console_ip: str = "", site_name: str = "default") -> str:
    """Fetch site settings including firmware channel via legacy API."""
    logger.info(f"get_site_settings for {console_ip} site={site_name}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    try:
        data = await _legacy_get(console_ip, site_name, "/get/setting")
        settings = data.get("data", [])
        lines = [f"✅ Site settings for '{site_name}' ({len(settings)} sections):\n"]
        for section in settings:
            key = section.get("key", "unknown")
            if key == "super_fwupdate":
                channels = section.get("available_firmware_channels", [])
                current = section.get("firmware_channel", "N/A")
                lines.append(f"  📦 Firmware Channel: {current}")
                lines.append(f"  📦 Available Channels: {', '.join(str(c) for c in channels)}")
                lines.append(f"  📦 SSO Enabled: {section.get('sso_enabled', 'N/A')}")
                lines.append(f"  📦 Controller Channel: {section.get('controller_channel', 'N/A')}")
                lines.append(f"  📦 FW Update ID: {section.get('_id', 'N/A')}")
            else:
                lines.append(f"  [{key}]")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"get_site_settings error: {e}")
        return f"❌ Error: {str(e)}"


# === CATEGORY 2: DEVICE MANAGEMENT ===

@mcp.tool()
async def list_devices(console_ip: str = "", site_id: str = "", filter_type: str = "") -> str:
    """List all devices for a site with optional type filter (ap, switch, unknown)."""
    logger.info(f"list_devices for {console_ip} site={site_id} filter={filter_type}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    try:
        devices = await _paginated_get(console_ip, f"/sites/{site_id}/devices")
        if filter_type.strip():
            devices = [d for d in devices if _detect_kind(d) == filter_type.strip().lower()]
        if not devices:
            return "⚠️ No devices found"
        lines = [f"✅ Found {len(devices)} device(s):\n"]
        for d in devices:
            kind = _detect_kind(d)
            lines.append(f"📡 [{kind.upper()}] {d.get('name', 'Unnamed')}")
            lines.append(_format_device(d))
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"list_devices error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def get_device_details(console_ip: str = "", site_id: str = "", device_id: str = "") -> str:
    """Get full device details including radios and ports for a specific device."""
    logger.info(f"get_device_details for {console_ip} device={device_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not device_id.strip():
        return "❌ Error: device_id is required"
    try:
        data = await _api_get(console_ip, f"/sites/{site_id}/devices/{device_id}")
        lines = [f"✅ Device Details:\n", _format_device(data)]
        interfaces = data.get("interfaces", {})
        radios = interfaces.get("radios", [])
        if radios:
            lines.append("\n  📻 Radios:")
            for r in radios:
                lines.append(
                    f"    - Band: {r.get('band', 'N/A')} | Channel: {r.get('channel', 'N/A')} | "
                    f"Width: {r.get('channelWidth', 'N/A')} | Power: {r.get('txPower', 'N/A')}dBm"
                )
        ports = interfaces.get("ports", [])
        if ports:
            lines.append("\n  🔌 Ports:")
            for p in ports:
                lines.append(
                    f"    - Port {p.get('idx', '?')}: {p.get('name', 'N/A')} | "
                    f"Speed: {p.get('speed', 'N/A')} | PoE: {p.get('poeEnabled', 'N/A')}"
                )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"get_device_details error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def get_device_statistics(console_ip: str = "", site_id: str = "", device_id: str = "") -> str:
    """Get latest device statistics including uptime, CPU, memory, and TX retries."""
    logger.info(f"get_device_statistics for {console_ip} device={device_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not device_id.strip():
        return "❌ Error: device_id is required"
    try:
        data = await _api_get(console_ip, f"/sites/{site_id}/devices/{device_id}/statistics/latest")
        uptime = data.get("uptime", "N/A")
        cpu = data.get("cpuUtilizationPercent", "N/A")
        mem = data.get("memoryUtilizationPercent", "N/A")
        tx_retries = data.get("txRetries", "N/A")
        return (
            f"📊 Device Statistics:\n"
            f"  ⏱️ Uptime: {uptime}s\n"
            f"  🖥️ CPU: {cpu}%\n"
            f"  💾 Memory: {mem}%\n"
            f"  📶 TX Retries: {tx_retries}\n"
            f"  Raw: {json.dumps(data, indent=2)}"
        )
    except Exception as e:
        logger.error(f"get_device_statistics error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def restart_device(console_ip: str = "", site_id: str = "", device_id: str = "") -> str:
    """Restart a UniFi device by sending RESTART action."""
    logger.info(f"restart_device for {console_ip} device={device_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not device_id.strip():
        return "❌ Error: device_id is required"
    try:
        payload = {"action": "RESTART"}
        data = await _api_post(console_ip, f"/sites/{site_id}/devices/{device_id}/actions", payload)
        return f"✅ Restart command sent to device {device_id}\n  Response: {json.dumps(data, indent=2)}"
    except Exception as e:
        logger.error(f"restart_device error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def power_cycle_port(console_ip: str = "", site_id: str = "", device_id: str = "", port_idx: str = "") -> str:
    """Power cycle a PoE port on a switch device."""
    logger.info(f"power_cycle_port for {console_ip} device={device_id} port={port_idx}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not device_id.strip():
        return "❌ Error: device_id is required"
    if not port_idx.strip():
        return "❌ Error: port_idx is required"
    try:
        payload = {"action": "POWER_CYCLE"}
        data = await _api_post(
            console_ip,
            f"/sites/{site_id}/devices/{device_id}/ports/{port_idx}/actions",
            payload,
        )
        return f"✅ Power cycle sent to port {port_idx} on device {device_id}\n  Response: {json.dumps(data, indent=2)}"
    except Exception as e:
        logger.error(f"power_cycle_port error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def adopt_device(console_ip: str = "", site_id: str = "", mac_address: str = "") -> str:
    """Adopt a device by MAC address into a site."""
    logger.info(f"adopt_device for {console_ip} mac={mac_address}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not mac_address.strip():
        return "❌ Error: mac_address is required"
    try:
        payload = {"macAddress": mac_address.strip()}
        data = await _api_post(console_ip, f"/sites/{site_id}/devices", payload)
        return f"✅ Adoption request sent for MAC {mac_address}\n  Response: {json.dumps(data, indent=2)}"
    except Exception as e:
        logger.error(f"adopt_device error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def list_pending_devices(console_ip: str = "") -> str:
    """List devices pending adoption on the console."""
    logger.info(f"list_pending_devices for {console_ip}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    try:
        data = await _api_get(console_ip, "/pending-devices")
        devices = data.get("data", [])
        if not devices:
            return "⚠️ No pending devices found"
        lines = [f"✅ Found {len(devices)} pending device(s):\n"]
        for d in devices:
            lines.append(
                f"  - MAC: {d.get('macAddress', 'N/A')} | Model: {d.get('model', 'N/A')} | "
                f"IP: {d.get('ipAddress', 'N/A')} | FW: {d.get('firmwareVersion', 'N/A')}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"list_pending_devices error: {e}")
        return f"❌ Error: {str(e)}"


# === CATEGORY 3: FIRMWARE OPERATIONS ===

@mcp.tool()
async def upgrade_device_channel(console_ip: str = "", site_name: str = "default", mac_address: str = "") -> str:
    """Upgrade a device to the current firmware channel release via legacy API."""
    logger.info(f"upgrade_device_channel for {console_ip} mac={mac_address}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not mac_address.strip():
        return "❌ Error: mac_address is required"
    try:
        payload = {"cmd": "upgrade", "mac": mac_address.strip().lower()}
        data = await _legacy_post(console_ip, site_name, "/cmd/devmgr", payload)
        return f"✅ Channel upgrade triggered for {mac_address}\n  Response: {json.dumps(data, indent=2)}"
    except Exception as e:
        logger.error(f"upgrade_device_channel error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def upgrade_device_custom(console_ip: str = "", site_name: str = "default", mac_address: str = "", firmware_url: str = "") -> str:
    """Upgrade a device with a custom firmware URL via legacy API."""
    logger.info(f"upgrade_device_custom for {console_ip} mac={mac_address} url={firmware_url}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not mac_address.strip():
        return "❌ Error: mac_address is required"
    if not firmware_url.strip():
        return "❌ Error: firmware_url is required"
    try:
        payload = {"cmd": "upgrade-external", "mac": mac_address.strip().lower(), "url": firmware_url.strip()}
        data = await _legacy_post(console_ip, site_name, "/cmd/devmgr", payload)
        return f"✅ Custom firmware upgrade triggered for {mac_address}\n  URL: {firmware_url}\n  Response: {json.dumps(data, indent=2)}"
    except Exception as e:
        logger.error(f"upgrade_device_custom error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def change_firmware_channel(console_ip: str = "", site_name: str = "default", channel: str = "") -> str:
    """Change firmware release channel then trigger firmware availability check."""
    logger.info(f"change_firmware_channel for {console_ip} channel={channel}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not channel.strip():
        return "❌ Error: channel is required (e.g., release, rc, beta)"
    try:
        settings_data = await _legacy_get(console_ip, site_name, "/get/setting")
        fw_settings = None
        for section in settings_data.get("data", []):
            if section.get("key") == "super_fwupdate":
                fw_settings = section
                break
        if fw_settings is None:
            return "❌ Error: Firmware update settings not found in site settings"
        available = fw_settings.get("available_firmware_channels", [])
        available_lower = [str(c).lower() for c in available]
        if channel.strip().lower() not in available_lower:
            return f"❌ Error: '{channel}' is not a valid channel. Available: {', '.join(str(c) for c in available)}"
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
            f"✅ Firmware channel changed to '{channel}'\n"
            f"  Previous available channels: {', '.join(str(c) for c in available)}\n"
            f"  ⏳ Firmware availability check triggered. Devices may take 30-60s to report new updates."
        )
    except Exception as e:
        logger.error(f"change_firmware_channel error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def check_firmware_updates(console_ip: str = "", site_name: str = "default") -> str:
    """Trigger a firmware availability check for all devices on a site."""
    logger.info(f"check_firmware_updates for {console_ip}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    try:
        payload = {"cmd": "list-available"}
        data = await _legacy_post(console_ip, site_name, "/cmd/firmware", payload)
        return f"✅ Firmware availability check triggered\n  Response: {json.dumps(data, indent=2)}"
    except Exception as e:
        logger.error(f"check_firmware_updates error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def bulk_upgrade_aps(console_ip: str = "", site_id: str = "", site_name: str = "default", firmware_url: str = "") -> str:
    """Bulk upgrade all online APs on a site — channel upgrade or custom URL if provided."""
    logger.info(f"bulk_upgrade_aps for {console_ip} site={site_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    try:
        devices = await _paginated_get(console_ip, f"/sites/{site_id}/devices")
        aps = [d for d in devices if _detect_kind(d) == "ap" and d.get("state") == "ONLINE"]
        if not aps:
            return "⚠️ No online APs found to upgrade"
        results = []
        for ap in aps:
            mac = ap.get("macAddress", "").lower()
            name = ap.get("name", "Unnamed")
            try:
                if firmware_url.strip():
                    payload = {"cmd": "upgrade-external", "mac": mac, "url": firmware_url.strip()}
                else:
                    if not ap.get("firmwareUpdatable", False):
                        results.append(f"  ⏭️ {name} ({mac}): Already up to date")
                        continue
                    payload = {"cmd": "upgrade", "mac": mac}
                await _legacy_post(console_ip, site_name, "/cmd/devmgr", payload)
                results.append(f"  ✅ {name} ({mac}): Upgrade triggered")
            except Exception as ap_err:
                results.append(f"  ❌ {name} ({mac}): {str(ap_err)}")
        header = f"⚡ Bulk AP Upgrade Results ({len(aps)} APs found):\n"
        return header + "\n".join(results)
    except Exception as e:
        logger.error(f"bulk_upgrade_aps error: {e}")
        return f"❌ Error: {str(e)}"


# === CATEGORY 4: WIFI BROADCASTS ===

@mcp.tool()
async def list_wifi_broadcasts(console_ip: str = "", site_id: str = "") -> str:
    """List all WiFi SSIDs (broadcasts) for a site."""
    logger.info(f"list_wifi_broadcasts for {console_ip} site={site_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    try:
        data = await _api_get(console_ip, f"/sites/{site_id}/wifi/broadcasts")
        broadcasts = data.get("data", [])
        if not broadcasts:
            return "⚠️ No WiFi broadcasts found"
        lines = [f"📶 Found {len(broadcasts)} WiFi broadcast(s):\n"]
        for b in broadcasts:
            enabled = "✅" if b.get("enabled", False) else "❌"
            lines.append(
                f"  {enabled} {b.get('name', 'Unnamed')} | ID: {b.get('id', 'N/A')} | "
                f"Security: {b.get('security', 'N/A')} | Band: {b.get('band', 'N/A')}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"list_wifi_broadcasts error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def get_wifi_broadcast(console_ip: str = "", site_id: str = "", broadcast_id: str = "") -> str:
    """Get details of a specific WiFi SSID broadcast."""
    logger.info(f"get_wifi_broadcast for {console_ip} broadcast={broadcast_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not broadcast_id.strip():
        return "❌ Error: broadcast_id is required"
    try:
        data = await _api_get(console_ip, f"/sites/{site_id}/wifi/broadcasts/{broadcast_id}")
        return f"📶 WiFi Broadcast Details:\n  {json.dumps(data, indent=2)}"
    except Exception as e:
        logger.error(f"get_wifi_broadcast error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def create_wifi_broadcast(console_ip: str = "", site_id: str = "", config_json: str = "") -> str:
    """Create a new WiFi SSID broadcast — provide config as JSON string."""
    logger.info(f"create_wifi_broadcast for {console_ip} site={site_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not config_json.strip():
        return "❌ Error: config_json is required (JSON string with SSID configuration)"
    try:
        payload = json.loads(config_json)
        data = await _api_post(console_ip, f"/sites/{site_id}/wifi/broadcasts", payload)
        return f"✅ WiFi broadcast created\n  Response: {json.dumps(data, indent=2)}"
    except json.JSONDecodeError as je:
        return f"❌ Error: Invalid JSON in config_json: {str(je)}"
    except Exception as e:
        logger.error(f"create_wifi_broadcast error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def update_wifi_broadcast(console_ip: str = "", site_id: str = "", broadcast_id: str = "", config_json: str = "") -> str:
    """Update an existing WiFi SSID broadcast — provide config as JSON string."""
    logger.info(f"update_wifi_broadcast for {console_ip} broadcast={broadcast_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not broadcast_id.strip():
        return "❌ Error: broadcast_id is required"
    if not config_json.strip():
        return "❌ Error: config_json is required (JSON string with updated SSID configuration)"
    try:
        payload = json.loads(config_json)
        data = await _api_put(console_ip, f"/sites/{site_id}/wifi/broadcasts/{broadcast_id}", payload)
        return f"✅ WiFi broadcast {broadcast_id} updated\n  Response: {json.dumps(data, indent=2)}"
    except json.JSONDecodeError as je:
        return f"❌ Error: Invalid JSON in config_json: {str(je)}"
    except Exception as e:
        logger.error(f"update_wifi_broadcast error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def delete_wifi_broadcast(console_ip: str = "", site_id: str = "", broadcast_id: str = "") -> str:
    """Delete a WiFi SSID broadcast by ID."""
    logger.info(f"delete_wifi_broadcast for {console_ip} broadcast={broadcast_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not broadcast_id.strip():
        return "❌ Error: broadcast_id is required"
    try:
        data = await _api_delete(console_ip, f"/sites/{site_id}/wifi/broadcasts/{broadcast_id}")
        return f"✅ WiFi broadcast {broadcast_id} deleted\n  Response: {json.dumps(data, indent=2)}"
    except Exception as e:
        logger.error(f"delete_wifi_broadcast error: {e}")
        return f"❌ Error: {str(e)}"


# === CATEGORY 5: CLIENT MANAGEMENT ===

@mcp.tool()
async def list_clients(console_ip: str = "", site_id: str = "", filter_type: str = "") -> str:
    """List connected clients for a site with optional type filter (WIRED, WIRELESS)."""
    logger.info(f"list_clients for {console_ip} site={site_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    try:
        clients = await _paginated_get(console_ip, f"/sites/{site_id}/clients")
        if filter_type.strip():
            clients = [c for c in clients if c.get("type", "").upper() == filter_type.strip().upper()]
        if not clients:
            return "⚠️ No clients found"
        lines = [f"✅ Found {len(clients)} client(s):\n"]
        for c in clients:
            lines.append(_format_client(c))
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"list_clients error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def get_client_details(console_ip: str = "", site_id: str = "", client_id: str = "") -> str:
    """Get detailed connection info for a specific client."""
    logger.info(f"get_client_details for {console_ip} client={client_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not client_id.strip():
        return "❌ Error: client_id is required"
    try:
        data = await _api_get(console_ip, f"/sites/{site_id}/clients/{client_id}")
        return f"✅ Client Details:\n  {json.dumps(data, indent=2)}"
    except Exception as e:
        logger.error(f"get_client_details error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def manage_guest_access(console_ip: str = "", site_id: str = "", client_id: str = "", action: str = "") -> str:
    """Authorize or unauthorize a guest client — action must be AUTHORIZE or UNAUTHORIZE."""
    logger.info(f"manage_guest_access for {console_ip} client={client_id} action={action}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not client_id.strip():
        return "❌ Error: client_id is required"
    if action.strip().upper() not in ("AUTHORIZE", "UNAUTHORIZE"):
        return "❌ Error: action must be AUTHORIZE or UNAUTHORIZE"
    try:
        payload = {"action": action.strip().upper()}
        data = await _api_post(console_ip, f"/sites/{site_id}/clients/{client_id}/actions", payload)
        return f"✅ Guest {action.strip().upper()} sent for client {client_id}\n  Response: {json.dumps(data, indent=2)}"
    except Exception as e:
        logger.error(f"manage_guest_access error: {e}")
        return f"❌ Error: {str(e)}"


# === CATEGORY 6: NETWORK MANAGEMENT ===

@mcp.tool()
async def list_networks(console_ip: str = "", site_id: str = "") -> str:
    """List all networks (VLANs) for a site."""
    logger.info(f"list_networks for {console_ip} site={site_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    try:
        data = await _api_get(console_ip, f"/sites/{site_id}/networks")
        networks = data.get("data", [])
        if not networks:
            return "⚠️ No networks found"
        lines = [f"🌐 Found {len(networks)} network(s):\n"]
        for n in networks:
            lines.append(
                f"  - {n.get('name', 'Unnamed')} | ID: {n.get('id', 'N/A')} | "
                f"VLAN: {n.get('vlan', 'N/A')} | Subnet: {n.get('subnet', 'N/A')} | "
                f"Purpose: {n.get('purpose', 'N/A')}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"list_networks error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def create_network(console_ip: str = "", site_id: str = "", config_json: str = "") -> str:
    """Create a new network (VLAN) — provide config as JSON string."""
    logger.info(f"create_network for {console_ip} site={site_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not config_json.strip():
        return "❌ Error: config_json is required (JSON string with network configuration)"
    try:
        payload = json.loads(config_json)
        data = await _api_post(console_ip, f"/sites/{site_id}/networks", payload)
        return f"✅ Network created\n  Response: {json.dumps(data, indent=2)}"
    except json.JSONDecodeError as je:
        return f"❌ Error: Invalid JSON in config_json: {str(je)}"
    except Exception as e:
        logger.error(f"create_network error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def update_network(console_ip: str = "", site_id: str = "", network_id: str = "", config_json: str = "") -> str:
    """Update an existing network (VLAN) — provide config as JSON string."""
    logger.info(f"update_network for {console_ip} network={network_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not network_id.strip():
        return "❌ Error: network_id is required"
    if not config_json.strip():
        return "❌ Error: config_json is required (JSON string with updated network configuration)"
    try:
        payload = json.loads(config_json)
        data = await _api_put(console_ip, f"/sites/{site_id}/networks/{network_id}", payload)
        return f"✅ Network {network_id} updated\n  Response: {json.dumps(data, indent=2)}"
    except json.JSONDecodeError as je:
        return f"❌ Error: Invalid JSON in config_json: {str(je)}"
    except Exception as e:
        logger.error(f"update_network error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def delete_network(console_ip: str = "", site_id: str = "", network_id: str = "") -> str:
    """Delete a network (VLAN) by ID."""
    logger.info(f"delete_network for {console_ip} network={network_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not network_id.strip():
        return "❌ Error: network_id is required"
    try:
        data = await _api_delete(console_ip, f"/sites/{site_id}/networks/{network_id}")
        return f"✅ Network {network_id} deleted\n  Response: {json.dumps(data, indent=2)}"
    except Exception as e:
        logger.error(f"delete_network error: {e}")
        return f"❌ Error: {str(e)}"


# === CATEGORY 7: HOTSPOT & FIREWALL ===

@mcp.tool()
async def list_vouchers(console_ip: str = "", site_id: str = "") -> str:
    """List all hotspot vouchers for a site."""
    logger.info(f"list_vouchers for {console_ip} site={site_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    try:
        data = await _api_get(console_ip, f"/sites/{site_id}/hotspot/vouchers")
        vouchers = data.get("data", [])
        if not vouchers:
            return "⚠️ No vouchers found"
        lines = [f"🎫 Found {len(vouchers)} voucher(s):\n"]
        for v in vouchers:
            lines.append(
                f"  - Code: {v.get('code', 'N/A')} | ID: {v.get('id', 'N/A')} | "
                f"Duration: {v.get('duration', 'N/A')}min | Used: {v.get('used', 0)}/{v.get('quota', 1)}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"list_vouchers error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def create_voucher(console_ip: str = "", site_id: str = "", config_json: str = "") -> str:
    """Create hotspot voucher(s) — provide config as JSON string with count, duration, etc."""
    logger.info(f"create_voucher for {console_ip} site={site_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not config_json.strip():
        return "❌ Error: config_json is required (JSON string with voucher configuration)"
    try:
        payload = json.loads(config_json)
        data = await _api_post(console_ip, f"/sites/{site_id}/hotspot/vouchers", payload)
        return f"✅ Voucher(s) created\n  Response: {json.dumps(data, indent=2)}"
    except json.JSONDecodeError as je:
        return f"❌ Error: Invalid JSON in config_json: {str(je)}"
    except Exception as e:
        logger.error(f"create_voucher error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def delete_voucher(console_ip: str = "", site_id: str = "", voucher_id: str = "") -> str:
    """Delete a hotspot voucher by ID."""
    logger.info(f"delete_voucher for {console_ip} voucher={voucher_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    if not voucher_id.strip():
        return "❌ Error: voucher_id is required"
    try:
        data = await _api_delete(console_ip, f"/sites/{site_id}/hotspot/vouchers/{voucher_id}")
        return f"✅ Voucher {voucher_id} deleted\n  Response: {json.dumps(data, indent=2)}"
    except Exception as e:
        logger.error(f"delete_voucher error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def list_firewall_policies(console_ip: str = "", site_id: str = "") -> str:
    """List firewall policies and zones for a site."""
    logger.info(f"list_firewall_policies for {console_ip} site={site_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    try:
        policies_data = await _api_get(console_ip, f"/sites/{site_id}/firewall/policies")
        zones_data = await _api_get(console_ip, f"/sites/{site_id}/firewall/zones")
        policies = policies_data.get("data", [])
        zones = zones_data.get("data", [])
        lines = [f"🔒 Firewall Overview:\n"]
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
        return f"❌ Error: {str(e)}"


# === CATEGORY 8: REPORTING ===

@mcp.tool()
async def generate_device_report(console_ip: str = "", site_id: str = "", site_name: str = "default") -> str:
    """Generate a markdown report of all devices with status, firmware, and stats saved to /reports/."""
    logger.info(f"generate_device_report for {console_ip} site={site_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    try:
        devices = await _paginated_get(console_ip, f"/sites/{site_id}/devices")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            f"# UniFi Device Report",
            f"",
            f"**Generated:** {now}",
            f"**Console:** {console_ip}",
            f"**Site ID:** {site_id}",
            f"**Total Devices:** {len(devices)}",
            f"",
            f"---",
            f"",
        ]
        ap_count = 0
        switch_count = 0
        other_count = 0
        for d in devices:
            kind = _detect_kind(d)
            if kind == "ap":
                ap_count += 1
            elif kind == "switch":
                switch_count += 1
            else:
                other_count += 1
            name = d.get("name", "Unnamed")
            state_icon = "🟢" if d.get("state") == "ONLINE" else "🔴"
            lines.append(f"## {state_icon} {name} [{kind.upper()}]")
            lines.append(f"")
            lines.append(f"| Property | Value |")
            lines.append(f"|----------|-------|")
            lines.append(f"| MAC | {d.get('macAddress', 'N/A')} |")
            lines.append(f"| Model | {d.get('model', 'N/A')} |")
            lines.append(f"| IP | {d.get('ipAddress', 'N/A')} |")
            lines.append(f"| State | {d.get('state', 'UNKNOWN')} |")
            lines.append(f"| Firmware | {d.get('firmwareVersion', 'N/A')} |")
            lines.append(f"| Updatable | {d.get('firmwareUpdatable', False)} |")
            lines.append(f"| ID | {d.get('id', 'N/A')} |")
            lines.append(f"")
            # Try to fetch stats for each device
            device_id = d.get("id", "")
            if device_id:
                try:
                    stats = await _api_get(console_ip, f"/sites/{site_id}/devices/{device_id}/statistics/latest")
                    lines.append(f"**Statistics:**")
                    lines.append(f"- Uptime: {stats.get('uptime', 'N/A')}s")
                    lines.append(f"- CPU: {stats.get('cpuUtilizationPercent', 'N/A')}%")
                    lines.append(f"- Memory: {stats.get('memoryUtilizationPercent', 'N/A')}%")
                    lines.append(f"")
                except Exception:
                    lines.append(f"*Statistics unavailable*")
                    lines.append(f"")
            lines.append(f"---")
            lines.append(f"")
        lines.append(f"## Summary")
        lines.append(f"")
        lines.append(f"- **APs:** {ap_count}")
        lines.append(f"- **Switches:** {switch_count}")
        lines.append(f"- **Other:** {other_count}")
        lines.append(f"- **Total:** {len(devices)}")
        content = "\n".join(lines)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"device_report_{timestamp}.md"
        filepath = _write_report(filename, content)
        return f"📁 Device report generated: {filepath}\n  Devices: {len(devices)} (APs: {ap_count}, Switches: {switch_count}, Other: {other_count})"
    except Exception as e:
        logger.error(f"generate_device_report error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def generate_wifi_report(console_ip: str = "", site_id: str = "") -> str:
    """Generate a markdown report of all SSIDs and wireless clients saved to /reports/."""
    logger.info(f"generate_wifi_report for {console_ip} site={site_id}")
    if not console_ip.strip():
        return "❌ Error: console_ip is required"
    if not site_id.strip():
        return "❌ Error: site_id is required"
    try:
        broadcasts_data = await _api_get(console_ip, f"/sites/{site_id}/wifi/broadcasts")
        broadcasts = broadcasts_data.get("data", [])
        clients = await _paginated_get(console_ip, f"/sites/{site_id}/clients")
        wireless_clients = [c for c in clients if c.get("type", "").upper() == "WIRELESS"]
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            f"# UniFi WiFi Report",
            f"",
            f"**Generated:** {now}",
            f"**Console:** {console_ip}",
            f"**Site ID:** {site_id}",
            f"",
            f"---",
            f"",
            f"## WiFi Broadcasts ({len(broadcasts)})",
            f"",
        ]
        if broadcasts:
            lines.append(f"| SSID | Enabled | Security | Band | ID |")
            lines.append(f"|------|---------|----------|------|----|")
            for b in broadcasts:
                enabled = "Yes" if b.get("enabled", False) else "No"
                lines.append(
                    f"| {b.get('name', 'N/A')} | {enabled} | "
                    f"{b.get('security', 'N/A')} | {b.get('band', 'N/A')} | {b.get('id', 'N/A')} |"
                )
            lines.append(f"")
        else:
            lines.append(f"*No WiFi broadcasts configured*")
            lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## Wireless Clients ({len(wireless_clients)})")
        lines.append(f"")
        if wireless_clients:
            lines.append(f"| Name | MAC | IP | Signal | SSID |")
            lines.append(f"|------|-----|----|--------|------|")
            for c in wireless_clients:
                name = c.get("name", c.get("hostname", "Unknown"))
                lines.append(
                    f"| {name} | {c.get('macAddress', 'N/A')} | "
                    f"{c.get('ipAddress', 'N/A')} | {c.get('signal', 'N/A')}dBm | "
                    f"{c.get('ssid', 'N/A')} |"
                )
            lines.append(f"")
        else:
            lines.append(f"*No wireless clients connected*")
            lines.append(f"")
        lines.append(f"## Summary")
        lines.append(f"")
        lines.append(f"- **Broadcasts:** {len(broadcasts)}")
        lines.append(f"- **Wireless Clients:** {len(wireless_clients)}")
        lines.append(f"- **Total Clients:** {len(clients)}")
        content = "\n".join(lines)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"wifi_report_{timestamp}.md"
        filepath = _write_report(filename, content)
        return f"📁 WiFi report generated: {filepath}\n  Broadcasts: {len(broadcasts)}, Wireless Clients: {len(wireless_clients)}"
    except Exception as e:
        logger.error(f"generate_wifi_report error: {e}")
        return f"❌ Error: {str(e)}"


# === SERVER STARTUP ===
if __name__ == "__main__":
    logger.info("Starting UniFi Network MCP server...")
    api_key = os.environ.get("UNIFI_API_KEY", "")
    if not api_key.strip():
        logger.warning("UNIFI_API_KEY not set — tools will fail until it is provided")
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
