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

## Long-Running Tools
- Claude Desktop has a hardcoded ~60s MCP tool timeout — long ramps will fail there
- Use Claude Code instead for long-running tests; it respects `MCP_TOOL_TIMEOUT`
- Project timeout is set to 60 minutes in `.claude/settings.json`
- Use `_execute_with_progress()` for any HTTP call that may exceed 15s — it sends progress keepalives via `anyio` task group to prevent client timeouts
- FastMCP `Context` is injected automatically via type hint (`ctx: Context = None`); it is hidden from the tool schema
- `ctx.report_progress(progress, total, message)` sends progress notifications; silently no-ops if ctx is None
- On failure mid-loop, return partial results with completed loop data and a resume hint

## ramp_loop Tool
- Each loop = forward ramp (original directions) + reverse ramp (A↔D flipped, E unchanged)
- `dry_run="true"` returns time estimate without executing — Claude should use this first
- Progress keepalives fire every 15s during each blocking HTTP request
- Partial failure reporting: returns all completed loop results plus which phase failed

## File Structure
- `adaura_rf_server.py` — Main MCP server with all tools
- `Dockerfile` — Python 3.11-slim, non-root user
- `requirements.txt` — mcp[cli]>=1.2.0, httpx
- `readme.txt` — Usage docs and installation instructions
- `adaura-rf-prompt.md` — Original prompt/API documentation
- `.mcp.json` — MCP server config for Claude Code (bare Python, no Docker)
- `.claude/settings.json` — Project-level Claude Code settings (MCP timeout)

## Development
```bash
# Bare Python (recommended for development)
# Configured in .mcp.json — restart MCP server via /mcp in Claude Code
python adaura_rf_server.py

# Test tool listing
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python adaura_rf_server.py

# Build Docker image (for distribution to other machines)
docker build -t adaura-rf-mcp-server .
```

## Deployment
- **Development**: bare Python via `.mcp.json` — edit code, `/mcp` restart, no rebuild
- **Distribution**: Docker image pushed to internal registry — other machines just `docker pull`, no git/Python needed
- Both use stdio transport (no network listeners, no attack surface)
- Docker config for Claude Desktop or distributed machines:
  ```json
  {"mcpServers": {"adaura-rf": {"command": "docker", "args": ["run", "--rm", "-i", "adaura-rf-mcp-server"]}}}
  ```

## Do NOT
- Use `@mcp.prompt()` decorators
- Pass `prompt` parameter to `FastMCP()`
- Use `None` as default parameter values (except `ctx: Context = None` which is framework-injected)
- Write multi-line docstrings on tools
- Hardcode IP addresses (always accept as parameter)
