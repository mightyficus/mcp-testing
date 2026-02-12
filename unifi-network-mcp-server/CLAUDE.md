# CLAUDE.md — UniFi Network MCP Server

## Overview

MCP server exposing 33 tools for managing UniFi Network consoles via Claude Desktop. Runs in Docker, communicates over stdio, uses FastMCP.

## Critical Coding Rules

These rules are **non-negotiable** — violating them breaks Claude Desktop:

1. **NO `@mcp.prompt()` decorators** — causes Claude Desktop crash
2. **NO `prompt` parameter to `FastMCP()`** — causes Claude Desktop crash
3. **NO type hints from `typing` module** — no `Optional`, `Union`, `List[str]`, etc.
4. **ALL parameters: `param: str = ""`** — never use `None` as default
5. **SINGLE-LINE docstrings only** — multi-line causes gateway panic errors
6. **ALL tools return `str`** — no other return types
7. **Check empty strings with `.strip()`** — not just truthiness
8. **Log to stderr only** — stdout is reserved for MCP protocol

## Architecture

```
unifi-network-mcp-server/
├── Dockerfile                  # python:3.11-slim, non-root mcpuser, /reports dir
├── requirements.txt            # mcp[cli]>=1.2.0, httpx
├── unifi_network_server.py     # All helpers + 33 tools + server startup
├── readme.txt                  # Full documentation
├── mcp-builder-prompt-unifi.md # NetworkChuck builder template (catalog/registry/config formats)
└── CLAUDE.md                   # This file
```

### Server Structure (unifi_network_server.py)

1. **Imports & logging** — stdlib + httpx + FastMCP, logging to stderr
2. **Internal helpers** (not tools):
   - `_get_headers()` — builds auth headers from `UNIFI_API_KEY` env var
   - `_api_url()` / `_legacy_url()` — URL builders for public and legacy APIs
   - `_api_get/post/put/delete()` — async HTTP for Integration API
   - `_legacy_get/post()` — async HTTP for legacy Network API
   - `_paginated_get()` — fetches all pages (200 per page)
   - `_format_device()` / `_format_client()` — dict → readable string
   - `_detect_kind()` — device type detection (ap/switch/unknown)
   - `_write_report()` — writes markdown to `/reports/`
3. **33 MCP tools** organized in 8 categories
4. **Server startup** — `mcp.run(transport="stdio")`

### API Surfaces

- **Public Integration API**: `https://{console}/proxy/network/integration/v1/...`
- **Legacy Network API**: `https://{console}/proxy/network/api/s/{siteName}/...`

Every tool accepts `console_ip: str = ""` since the IP may vary between consoles.

## How to Add a New Tool

```python
@mcp.tool()
async def my_new_tool(console_ip: str = "", site_id: str = "", my_param: str = "") -> str:
    """Single-line description of what this tool does."""
    logger.info(f"my_new_tool for {console_ip}")
    if not console_ip.strip():
        return "Error: console_ip is required"
    if not my_param.strip():
        return "Error: my_param is required"
    try:
        data = await _api_get(console_ip, f"/sites/{site_id}/some/endpoint")
        return f"Success: {json.dumps(data, indent=2)}"
    except Exception as e:
        logger.error(f"my_new_tool error: {e}")
        return f"Error: {str(e)}"
```

After adding, also:
1. Add `- name: my_new_tool` to `custom.yaml` catalog
2. Rebuild: `docker build -t unifi-network-mcp-server .`

## Tool Categories

| # | Category | Tools | API |
|---|----------|-------|-----|
| 1 | System & Site Info | 3 | Public + Legacy |
| 2 | Device Management | 7 | Public |
| 3 | Firmware Operations | 5 | Legacy |
| 4 | WiFi Broadcasts | 5 | Public |
| 5 | Client Management | 3 | Public |
| 6 | Network Management | 4 | Public |
| 7 | Hotspot & Firewall | 4 | Public |
| 8 | Reporting | 2 | Public (multi-call) |

## Testing

```bash
# Build
docker build -t unifi-network-mcp-server .

# Smoke test (should return JSON with 33 tools)
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | docker run -i --rm -e UNIFI_API_KEY=test unifi-network-mcp-server

# Test with real console
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_app_info","arguments":{"console_ip":"192.168.1.1"}},"id":2}' | docker run -i --rm -e UNIFI_API_KEY=your-key unifi-network-mcp-server
```

## Builder Prompt

The full MCP server builder prompt (NetworkChuck template) is in `mcp-builder-prompt-unifi.md` in this directory. It contains the Docker catalog YAML format, registry entries, Claude Desktop config JSON structure, and all coding rule rationale.

## Reference API Patterns

These patterns were extracted from the parent `unifi/` Python library and adapted for async httpx in this server. They document the **actual UniFi API behavior** that the tools rely on.

### Firmware Channel Change Workflow

Used by `change_firmware_channel` tool. The workflow is: GET settings → find `super_fwupdate` section → POST new channel → POST `cmd/firmware` to trigger availability check.

```python
# Original: unifi/site.py changeFirmwareChannel()
# 1. GET .../get/setting → find section where key == "super_fwupdate"
# 2. Validate channel against available_firmware_channels list
# 3. POST .../set/setting/super_fwupdate with payload:
payload = {
    "key": "super_fwupdate",
    "sso_enabled": fwSettings.get("sso_enabled"),
    "controller_channel": fwSettings.get("controller_channel"),
    "firmware_channel": channel,
    "_id": fwSettings.get("_id"),
}
# 4. POST .../cmd/firmware with {"cmd": "list-available"} to trigger update check
# Note: Original code sleeps 15s after channel change, 45s after firmware check.
#       The MCP server does NOT sleep — the caller can poll if needed.
```

### Pagination Pattern

Used by `_paginated_get()` helper. The Integration API defaults to 25 items; we fetch in chunks of 200.

```python
# Original: unifi/site.py _requestDeviceList()
# 1. First call: GET base URL → response["totalCount"] gives total
# 2. Loop: GET base?limit={chunk}&offset={fetched} until fetched >= total
# 3. Safety: break if a page returns empty data (avoids infinite loop if API misreports)
# 4. Warn (don't fail) if final count != totalCount (inventory can change mid-paginate)
page_size = 200
fetched = 0
while fetched < total:
    limit = min(page_size, total - fetched)
    # GET f"{base}?limit={limit}&offset={fetched}"
    data = page.get("data", [])
    all_data.extend(data)
    fetched += len(data)
    if len(data) == 0:
        break
```

### Device Upgrade Logic

Used by `upgrade_device_channel`, `upgrade_device_custom`, and `bulk_upgrade_aps` tools. Two variants via legacy POST to `.../cmd/devmgr`:

```python
# Original: unifi/device.py upgradeDevice()
# Channel upgrade (use current release channel firmware):
payload = {"cmd": "upgrade", "mac": device_mac}

# Custom URL upgrade (specific firmware binary):
payload = {"cmd": "upgrade-external", "mac": device_mac, "url": firmware_url}

# Notes:
# - MAC must be lowercase
# - Channel upgrade: check device.firmwareUpdatable first; skip if already current
# - Custom URL upgrade: format is [ftp|http|https]://path.to/update.[bin|tar]
# - Original code retries twice with progressive backoff polling for state == "UPDATING"
#   The MCP server fires and returns immediately — caller can poll device state.
```

### Device Kind Detection

Used by `_detect_kind()` helper and `bulk_upgrade_aps` (to filter APs).

```python
# Original: unifi/_utils.py detectKind()
# device["features"] is a list like ["accessPoint"] or ["switching"] or both
# Priority logic:
#   1. "accessPoint" in features AND "switching" NOT in features → "ap"
#   2. Both present → check device["interfaces"]["radios"]; if present → "ap"
#   3. "switching" in features → "switch"
#   4. Otherwise → "unknown"
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
```
