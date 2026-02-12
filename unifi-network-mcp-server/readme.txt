# UniFi Network MCP Server

A Model Context Protocol (MCP) server that provides full control over UniFi Network devices, firmware, WiFi, networks, and more — designed for stress-testing AP firmware and managing UniFi infrastructure via Claude Desktop.

## Purpose

This MCP server provides a secure interface for AI assistants to manage UniFi Network consoles, including device management, firmware upgrades, WiFi SSID control, network/VLAN management, hotspot vouchers, firewall policies, and generating markdown reports.

## Features

### Category 1: System & Site Info
- **`get_app_info`** - Get UniFi Console application info including version
- **`list_sites`** - List all UniFi sites with their IDs and names
- **`get_site_settings`** - Fetch site settings including firmware channel via legacy API

### Category 2: Device Management
- **`list_devices`** - List all devices for a site with optional type filter (ap, switch, unknown)
- **`get_device_details`** - Get full device details including radios and ports
- **`get_device_statistics`** - Get latest device statistics (uptime, CPU, memory, TX retries)
- **`restart_device`** - Restart a UniFi device by sending RESTART action
- **`power_cycle_port`** - Power cycle a PoE port on a switch device
- **`adopt_device`** - Adopt a device by MAC address into a site
- **`list_pending_devices`** - List devices pending adoption on the console

### Category 3: Firmware Operations (Stress Testing Core)
- **`upgrade_device_channel`** - Upgrade a device to the current firmware channel release
- **`upgrade_device_custom`** - Upgrade a device with a custom firmware URL
- **`change_firmware_channel`** - Change firmware release channel then trigger availability check
- **`check_firmware_updates`** - Trigger a firmware availability check for all devices
- **`bulk_upgrade_aps`** - Bulk upgrade all online APs on a site

### Category 4: WiFi Broadcasts
- **`list_wifi_broadcasts`** - List all WiFi SSIDs (broadcasts) for a site
- **`get_wifi_broadcast`** - Get details of a specific WiFi SSID broadcast
- **`create_wifi_broadcast`** - Create a new WiFi SSID broadcast
- **`update_wifi_broadcast`** - Update an existing WiFi SSID broadcast
- **`delete_wifi_broadcast`** - Delete a WiFi SSID broadcast by ID

### Category 5: Client Management
- **`list_clients`** - List connected clients with optional type filter (WIRED, WIRELESS)
- **`get_client_details`** - Get detailed connection info for a specific client
- **`manage_guest_access`** - Authorize or unauthorize a guest client

### Category 6: Network Management
- **`list_networks`** - List all networks (VLANs) for a site
- **`create_network`** - Create a new network (VLAN)
- **`update_network`** - Update an existing network (VLAN)
- **`delete_network`** - Delete a network (VLAN) by ID

### Category 7: Hotspot & Firewall
- **`list_vouchers`** - List all hotspot vouchers for a site
- **`create_voucher`** - Create hotspot voucher(s)
- **`delete_voucher`** - Delete a hotspot voucher by ID
- **`list_firewall_policies`** - List firewall policies and zones for a site

### Category 8: Reporting
- **`generate_device_report`** - Generate a markdown report of all devices with status/firmware/stats
- **`generate_wifi_report`** - Generate a markdown report of SSIDs and wireless clients

## Prerequisites

- Docker Desktop with MCP Toolkit enabled
- Docker MCP CLI plugin (`docker mcp` command)
- A UniFi Network Console with API key (Network 10.1.68+)
- The console IP must be reachable from the Docker container

## Installation

### Step 1: Save the Files

Save all 5 files (Dockerfile, requirements.txt, unifi_network_server.py, readme.txt, CLAUDE.md) into a directory called `unifi-network-mcp-server/`.

### Step 2: Build Docker Image

    docker build -t unifi-network-mcp-server .

### Step 3: Set Up Secrets

    docker mcp secret set UNIFI_API_KEY="your-api-key-here"
    docker mcp secret list

### Step 4: Create Custom Catalog

    mkdir -p ~/.docker/mcp/catalogs

Create or edit `~/.docker/mcp/catalogs/custom.yaml`:

    version: 2
    name: custom
    displayName: Custom MCP Servers
    registry:
      unifi-network:
        description: "Manage UniFi Network devices, firmware, WiFi, and networks"
        title: "UniFi Network"
        type: server
        dateAdded: "2026-02-11T00:00:00Z"
        image: unifi-network-mcp-server:latest
        ref: ""
        readme: ""
        toolsUrl: ""
        source: ""
        upstream: ""
        icon: ""
        tools:
          - name: get_app_info
          - name: list_sites
          - name: get_site_settings
          - name: list_devices
          - name: get_device_details
          - name: get_device_statistics
          - name: restart_device
          - name: power_cycle_port
          - name: adopt_device
          - name: list_pending_devices
          - name: upgrade_device_channel
          - name: upgrade_device_custom
          - name: change_firmware_channel
          - name: check_firmware_updates
          - name: bulk_upgrade_aps
          - name: list_wifi_broadcasts
          - name: get_wifi_broadcast
          - name: create_wifi_broadcast
          - name: update_wifi_broadcast
          - name: delete_wifi_broadcast
          - name: list_clients
          - name: get_client_details
          - name: manage_guest_access
          - name: list_networks
          - name: create_network
          - name: update_network
          - name: delete_network
          - name: list_vouchers
          - name: create_voucher
          - name: delete_voucher
          - name: list_firewall_policies
          - name: generate_device_report
          - name: generate_wifi_report
        secrets:
          - name: UNIFI_API_KEY
            env: UNIFI_API_KEY
            example: "your-unifi-api-key"
        metadata:
          category: automation
          tags:
            - unifi
            - network
            - firmware
            - wifi
          license: MIT
          owner: local

### Step 5: Update Registry

Edit `~/.docker/mcp/registry.yaml` and add under the `registry:` key:

    registry:
      # ... existing servers ...
      unifi-network:
        ref: ""

### Step 6: Configure Claude Desktop

Find your Claude Desktop config:
- macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
- Windows: %APPDATA%\Claude\claude_desktop_config.json
- Linux: ~/.config/Claude/claude_desktop_config.json

Add the custom catalog line to your args array:

    {
      "mcpServers": {
        "mcp-toolkit-gateway": {
          "command": "docker",
          "args": [
            "run", "-i", "--rm",
            "-v", "/var/run/docker.sock:/var/run/docker.sock",
            "-v", "YOUR_HOME/.docker/mcp:/mcp",
            "docker/mcp-gateway",
            "--catalog=/mcp/catalogs/docker-mcp.yaml",
            "--catalog=/mcp/catalogs/custom.yaml",
            "--config=/mcp/config.yaml",
            "--registry=/mcp/registry.yaml",
            "--tools-config=/mcp/tools.yaml",
            "--transport=stdio"
          ]
        }
      }
    }

Replace YOUR_HOME with your actual home directory path.

### Step 7: Restart Claude Desktop

Quit and restart Claude Desktop. Your 33 UniFi Network tools should appear.

## Usage Examples

In Claude Desktop, you can ask:
- "What version is my UniFi console at 192.168.1.1?"
- "List all sites on console 10.0.0.1"
- "Show me all APs on site abc-123"
- "Upgrade all APs to the latest firmware"
- "Change the firmware channel to beta on my default site"
- "Create a guest WiFi network called 'Visitors'"
- "List all connected wireless clients"
- "Generate a device report for my network"
- "Power cycle port 5 on switch xyz-456"
- "Show me the firewall policies"
- "Create a hotspot voucher for 24 hours"

## Architecture

    Claude Desktop -> MCP Gateway -> UniFi Network MCP Server -> UniFi Console API
                                            |
                                     Docker Desktop Secrets
                                       (UNIFI_API_KEY)

The server uses two API surfaces:
- Public Integration API: https://{console}/proxy/network/integration/v1/...
- Legacy Network API: https://{console}/proxy/network/api/s/{siteName}/...

Reports are written to /reports/ inside the container (mountable as a Docker volume).

## Development

### Local Testing

    export UNIFI_API_KEY="your-test-key"
    python unifi_network_server.py

### MCP Protocol Test

    echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python unifi_network_server.py

### Docker Test

    echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | docker run -i --rm -e UNIFI_API_KEY=test unifi-network-mcp-server

### Adding New Tools

1. Add the async function to unifi_network_server.py
2. Decorate with @mcp.tool()
3. Use SINGLE-LINE docstring only
4. All parameters must be str with default ""
5. Return a formatted string
6. Update the catalog entry with the new tool name
7. Rebuild the Docker image

## Troubleshooting

### Tools Not Appearing
- Verify Docker image built successfully
- Check catalog and registry files
- Ensure Claude Desktop config includes custom catalog line
- Restart Claude Desktop

### Authentication Errors
- Verify secrets with `docker mcp secret list`
- Ensure secret names match in code and catalog
- Verify your API key has Network permissions on the console

### Connection Errors
- Ensure the console IP is reachable from the Docker container
- TLS verification is off by default (self-signed certs are common on UDMs)
- Check that the console is running Network 10.1.68+

### Report Not Generated
- Mount /reports as a Docker volume: `-v ./reports:/reports`
- Ensure the mcpuser has write permissions

## Security Considerations

- API key stored in Docker Desktop secrets (never hardcoded)
- Running as non-root user (mcpuser)
- TLS verification off by default (UniFi consoles typically use self-signed certs)
- Sensitive data never logged to stdout

## License

MIT License
