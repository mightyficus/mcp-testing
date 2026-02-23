# AdauraRF 8-Channel MCP Server

A Model Context Protocol (MCP) server for controlling an AdauraTech 8-channel
programmable RF attenuator via its RESTful API.

## Purpose

This MCP server provides an interface for AI assistants to control RF attenuation
levels on an AdauraTech 8-channel attenuator. It is designed for lab environments
where WiFi roaming events are simulated by ramping attenuation on different channels.

## Features

### Tools

- **`set_attenuation`** - Set attenuation on a single channel
- **`set_all_attenuation`** - Set attenuation on all channels (uniform or per-channel)
- **`ramp_channels`** - Ramp (fade) attenuation across channels with pre/post status checks
- **`randomize_channel`** - Set a channel to a random attenuation within a range
- **`randomize_all_channels`** - Randomize all channels (consistent or independent values)
- **`get_status`** - Get current attenuation levels for all channels
- **`get_device_info`** - Get device model, serial, firmware, and network info

## Prerequisites

- Docker Desktop with MCP Toolkit enabled
- Docker MCP CLI plugin (`docker mcp` command)
- Network access to the AdauraRF attenuator

## Installation

1. Build the Docker image:

   docker build -t adaura-rf-mcp-server .

2. Create custom catalog at ~/.docker/mcp/catalogs/custom.yaml:

   version: 2
   name: custom
   displayName: Custom MCP Servers
   registry:
     adaura-rf:
       description: "Control AdauraTech 8-channel RF attenuator"
       title: "AdauraRF Attenuator"
       type: server
       dateAdded: "2026-02-23T00:00:00Z"
       image: adaura-rf-mcp-server:latest
       ref: ""
       readme: ""
       toolsUrl: ""
       source: ""
       upstream: ""
       icon: ""
       tools:
         - name: set_attenuation
         - name: set_all_attenuation
         - name: ramp_channels
         - name: randomize_channel
         - name: randomize_all_channels
         - name: get_status
         - name: get_device_info
       metadata:
         category: automation
         tags:
           - rf
           - attenuator
           - wifi
           - lab
         license: MIT
         owner: local

3. Add to ~/.docker/mcp/registry.yaml under the registry: key:

   adaura-rf:
     ref: ""

4. Ensure Claude Desktop config includes the custom catalog in args:

   "--catalog=/mcp/catalogs/custom.yaml"

5. Restart Claude Desktop.

## Usage Examples

In Claude Desktop, you can ask:

- "Get the status of the attenuator at 192.168.10.87"
- "Set channel 1 to 30 dB on 192.168.10.87"
- "Set all channels to 0 dB on 192.168.10.87"
- "Ramp channels 1-4 up from 0 to 30 dB while ramping 5-8 down, step 0.5, dwell 100ms"
- "Randomize all channels between 10 and 50 dB"
- "Get device info from 192.168.10.87"

## Architecture

Claude Desktop -> MCP Gateway -> AdauraRF MCP Server -> AdauraRF Attenuator REST API
                                       |
                                 HTTP Basic Auth
                              (default: admin:admin)

## Development

### Local Testing

  # Run directly
  python adaura_rf_server.py

  # Test MCP protocol
  echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python adaura_rf_server.py

### Adding New Tools

1. Add the function to adaura_rf_server.py
2. Decorate with @mcp.tool()
3. Use single-line docstrings only
4. Default all params to empty strings
5. Update the catalog entry with the new tool name
6. Rebuild the Docker image

## Troubleshooting

### Tools Not Appearing
- Verify Docker image built successfully
- Check catalog and registry files
- Ensure Claude Desktop config includes custom catalog
- Restart Claude Desktop

### Connection Errors
- Verify the attenuator IP is reachable from Docker
- Check that HTTP Basic Auth credentials are correct (default: admin:admin)
- Ensure the attenuator's web interface is accessible

### Ramp Timeout
- RAMP requests block until complete; long ramps need time
- The server uses a generous timeout (estimated duration + 30s)
- If timeouts occur, try shorter ramp ranges or larger step sizes

## Security Considerations

- Authentication uses HTTP Basic Auth (default admin:admin)
- Override credentials by passing username/password to each tool
- Running as non-root user in Docker
- No credentials are stored or logged

## License

MIT License
