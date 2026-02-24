#!/usr/bin/env python3
"""UniFi Network MCP Server — entrypoint that registers all tool modules and runs the server."""

import os
import sys

from mcp.server.fastmcp import FastMCP
from helpers import logger

# Initialize MCP server - NO PROMPT PARAMETER
mcp = FastMCP("unifi-network")

# Register all tool modules
from tools import system_site, devices, firmware, wifi, clients, networks, hotspot_firewall, reporting

for mod in [system_site, devices, firmware, wifi, clients, networks, hotspot_firewall, reporting]:
    mod.register(mcp)

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
