#!/usr/bin/env python3
"""Internal helpers, logging setup, and constants for the UniFi Network MCP Server."""

import os
import sys
import json
import logging
from datetime import datetime, timezone

import httpx

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("unifi-network-server")

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
