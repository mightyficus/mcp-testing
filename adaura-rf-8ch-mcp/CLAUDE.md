# AdauraRF 8-Channel MCP Server

## Project Overview
MCP server for controlling an AdauraTech 8-channel programmable RF attenuator via REST API. Used in lab environments to simulate WiFi roaming by ramping attenuation on different channels.

## API Details
- Base URL: `http://<IP>/execute.php?CMD+PARAM+PARAM+...`
- Auth: HTTP Basic Auth (default admin:admin)
- Commands: SET, SAA, RAMP, RAND, RANDALL, STATUS, INFO

## Key Conventions
- All tool parameters default to `""` (empty strings), never `None`
- No complex type hints (no Optional, Union, List, etc.)
- Single-line docstrings only (multi-line causes gateway panic errors)
- All tools return formatted strings with emoji indicators
- Use `httpx.AsyncClient` with `httpx.BasicAuth`

## RAMP Command Quirks
- All 8 channel directions must be specified (A=Ascend, D=Descend, E=Exclude)
- Decimal parameters MUST include trailing digits (use `:.2f` formatting)
- The HTTP request blocks until the ramp finishes
- Estimated duration: `((atten_stop - atten_start) / step) * dwell` ms
- Response only shows first ~40 steps; use STATUS before/after to verify
- Set httpx timeout to `estimated_duration + 30s`

## File Structure
- `adaura_rf_server.py` — Main MCP server with all tools
- `Dockerfile` — Python 3.11-slim, non-root user
- `requirements.txt` — mcp[cli]>=1.2.0, httpx
- `readme.txt` — Usage docs and installation instructions
- `adaura-rf-prompt.md` — Original prompt/API documentation

## Development
```bash
# Test locally
python adaura_rf_server.py

# Test tool listing
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python adaura_rf_server.py

# Build Docker image
docker build -t adaura-rf-mcp-server .
```

## Do NOT
- Use `@mcp.prompt()` decorators
- Pass `prompt` parameter to `FastMCP()`
- Use `None` as default parameter values
- Write multi-line docstrings on tools
- Hardcode IP addresses (always accept as parameter)
