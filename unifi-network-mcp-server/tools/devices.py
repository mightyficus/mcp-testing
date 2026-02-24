"""Category 2: Device Management tools."""

import json
from helpers import _api_get, _api_post, _paginated_get, _format_device, _detect_kind, logger


def register(mcp):

    @mcp.tool()
    async def list_devices(console_ip: str = "", site_id: str = "", filter_type: str = "") -> str:
        """List all devices for a site with optional type filter (ap, switch, unknown)."""
        logger.info(f"list_devices for {console_ip} site={site_id} filter={filter_type}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        try:
            devices = await _paginated_get(console_ip, f"/sites/{site_id}/devices")
            if filter_type.strip():
                devices = [d for d in devices if _detect_kind(d) == filter_type.strip().lower()]
            if not devices:
                return "No devices found"
            lines = [f"Found {len(devices)} device(s):\n"]
            for d in devices:
                kind = _detect_kind(d)
                lines.append(f"[{kind.upper()}] {d.get('name', 'Unnamed')}")
                lines.append(_format_device(d))
                lines.append("")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"list_devices error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def get_device_details(console_ip: str = "", site_id: str = "", device_id: str = "") -> str:
        """Get full device details including radios and ports for a specific device."""
        logger.info(f"get_device_details for {console_ip} device={device_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not device_id.strip():
            return "Error: device_id is required"
        try:
            data = await _api_get(console_ip, f"/sites/{site_id}/devices/{device_id}")
            lines = [f"Device Details:\n", _format_device(data)]
            interfaces = data.get("interfaces", {})
            radios = interfaces.get("radios", [])
            if radios:
                lines.append("\n  Radios:")
                for r in radios:
                    lines.append(
                        f"    - Band: {r.get('band', 'N/A')} | Channel: {r.get('channel', 'N/A')} | "
                        f"Width: {r.get('channelWidth', 'N/A')} | Power: {r.get('txPower', 'N/A')}dBm"
                    )
            ports = interfaces.get("ports", [])
            if ports:
                lines.append("\n  Ports:")
                for p in ports:
                    lines.append(
                        f"    - Port {p.get('idx', '?')}: {p.get('name', 'N/A')} | "
                        f"Speed: {p.get('speed', 'N/A')} | PoE: {p.get('poeEnabled', 'N/A')}"
                    )
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"get_device_details error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def get_device_statistics(console_ip: str = "", site_id: str = "", device_id: str = "") -> str:
        """Get latest device statistics including uptime, CPU, memory, and TX retries."""
        logger.info(f"get_device_statistics for {console_ip} device={device_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not device_id.strip():
            return "Error: device_id is required"
        try:
            data = await _api_get(console_ip, f"/sites/{site_id}/devices/{device_id}/statistics/latest")
            uptime = data.get("uptime", "N/A")
            cpu = data.get("cpuUtilizationPercent", "N/A")
            mem = data.get("memoryUtilizationPercent", "N/A")
            tx_retries = data.get("txRetries", "N/A")
            return (
                f"Device Statistics:\n"
                f"  Uptime: {uptime}s\n"
                f"  CPU: {cpu}%\n"
                f"  Memory: {mem}%\n"
                f"  TX Retries: {tx_retries}\n"
                f"  Raw: {json.dumps(data, indent=2)}"
            )
        except Exception as e:
            logger.error(f"get_device_statistics error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def restart_device(console_ip: str = "", site_id: str = "", device_id: str = "") -> str:
        """Restart a UniFi device by sending RESTART action."""
        logger.info(f"restart_device for {console_ip} device={device_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not device_id.strip():
            return "Error: device_id is required"
        try:
            payload = {"action": "RESTART"}
            data = await _api_post(console_ip, f"/sites/{site_id}/devices/{device_id}/actions", payload)
            return f"Restart command sent to device {device_id}\n  Response: {json.dumps(data, indent=2)}"
        except Exception as e:
            logger.error(f"restart_device error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def power_cycle_port(console_ip: str = "", site_id: str = "", device_id: str = "", port_idx: str = "") -> str:
        """Power cycle a PoE port on a switch device."""
        logger.info(f"power_cycle_port for {console_ip} device={device_id} port={port_idx}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not device_id.strip():
            return "Error: device_id is required"
        if not port_idx.strip():
            return "Error: port_idx is required"
        try:
            payload = {"action": "POWER_CYCLE"}
            data = await _api_post(
                console_ip,
                f"/sites/{site_id}/devices/{device_id}/ports/{port_idx}/actions",
                payload,
            )
            return f"Power cycle sent to port {port_idx} on device {device_id}\n  Response: {json.dumps(data, indent=2)}"
        except Exception as e:
            logger.error(f"power_cycle_port error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def adopt_device(console_ip: str = "", site_id: str = "", mac_address: str = "") -> str:
        """Adopt a device by MAC address into a site."""
        logger.info(f"adopt_device for {console_ip} mac={mac_address}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
        if not mac_address.strip():
            return "Error: mac_address is required"
        try:
            payload = {"macAddress": mac_address.strip()}
            data = await _api_post(console_ip, f"/sites/{site_id}/devices", payload)
            return f"Adoption request sent for MAC {mac_address}\n  Response: {json.dumps(data, indent=2)}"
        except Exception as e:
            logger.error(f"adopt_device error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def list_pending_devices(console_ip: str = "") -> str:
        """List devices pending adoption on the console."""
        logger.info(f"list_pending_devices for {console_ip}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        try:
            data = await _api_get(console_ip, "/pending-devices")
            devices = data.get("data", [])
            if not devices:
                return "No pending devices found"
            lines = [f"Found {len(devices)} pending device(s):\n"]
            for d in devices:
                lines.append(
                    f"  - MAC: {d.get('macAddress', 'N/A')} | Model: {d.get('model', 'N/A')} | "
                    f"IP: {d.get('ipAddress', 'N/A')} | FW: {d.get('firmwareVersion', 'N/A')}"
                )
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"list_pending_devices error: {e}")
            return f"Error: {str(e)}"
