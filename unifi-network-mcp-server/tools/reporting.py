"""Category 8: Reporting tools."""

import json
from datetime import datetime, timezone
from helpers import _api_get, _paginated_get, _detect_kind, _write_report, logger


def register(mcp):

    @mcp.tool()
    async def generate_device_report(console_ip: str = "", site_id: str = "", site_name: str = "default") -> str:
        """Generate a markdown report of all devices with status, firmware, and stats saved to /reports/."""
        logger.info(f"generate_device_report for {console_ip} site={site_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
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
                state_icon = "ONLINE" if d.get("state") == "ONLINE" else "OFFLINE"
                lines.append(f"## [{state_icon}] {name} [{kind.upper()}]")
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
            return f"Device report generated: {filepath}\n  Devices: {len(devices)} (APs: {ap_count}, Switches: {switch_count}, Other: {other_count})\n\n{content}"
        except Exception as e:
            logger.error(f"generate_device_report error: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def generate_wifi_report(console_ip: str = "", site_id: str = "") -> str:
        """Generate a markdown report of all SSIDs and wireless clients saved to /reports/."""
        logger.info(f"generate_wifi_report for {console_ip} site={site_id}")
        if not console_ip.strip():
            return "Error: console_ip is required"
        if not site_id.strip():
            return "Error: site_id is required"
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
            return f"WiFi report generated: {filepath}\n  Broadcasts: {len(broadcasts)}, Wireless Clients: {len(wireless_clients)}\n\n{content}"
        except Exception as e:
            logger.error(f"generate_wifi_report error: {e}")
            return f"Error: {str(e)}"
