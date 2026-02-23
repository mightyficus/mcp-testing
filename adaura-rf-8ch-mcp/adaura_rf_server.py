#!/usr/bin/env python3
"""Simple AdauraRF 8-Channel MCP Server - Controls programmable RF attenuators via REST API."""

import sys
import logging

import anyio
import httpx
from mcp.server.fastmcp import FastMCP, Context

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("adaura-rf-server")

# Initialize MCP server
mcp = FastMCP("adaura-rf")


# === UTILITY FUNCTIONS ===

async def _execute_command(ip_address: str, command: str, username: str, password: str, timeout: float = 10.0) -> str:
    """Execute a command against the AdauraRF attenuator API."""
    url = f"http://{ip_address}/execute.php?{command}"
    auth = httpx.BasicAuth(username, password)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, auth=auth, timeout=timeout)
        response.raise_for_status()
        return response.text


async def _execute_with_progress(ip_address: str, command: str, username: str, password: str, timeout: float, ctx: Context, progress: float, total: float, message: str) -> str:
    """Execute a long-running command while sending periodic progress keepalives."""
    result_holder = []

    async def do_request(task_status=anyio.TASK_STATUS_IGNORED):
        task_status.started()
        resp = await _execute_command(ip_address, command, username, password, timeout=timeout)
        result_holder.append(resp)
        tg.cancel_scope.cancel()

    async def send_keepalives():
        elapsed = 0
        while True:
            await anyio.sleep(15)
            elapsed += 15
            if ctx:
                await ctx.report_progress(progress, total, f"{message} ({elapsed}s elapsed)")

    async with anyio.create_task_group() as tg:
        await tg.start(do_request)
        tg.start_soon(send_keepalives)

    return result_holder[0]


# === MCP TOOLS ===

@mcp.tool()
async def set_attenuation(ip_address: str = "", channel: str = "", attenuation: str = "", username: str = "admin", password: str = "admin") -> str:
    """Set attenuation level on a single channel of the AdauraRF attenuator."""
    if not ip_address.strip():
        return "❌ Error: ip_address is required"
    if not channel.strip():
        return "❌ Error: channel is required (1-8)"
    if not attenuation.strip():
        return "❌ Error: attenuation value is required"

    try:
        ch = int(channel.strip())
        atten = float(attenuation.strip())
    except ValueError:
        return "❌ Error: channel must be an integer and attenuation must be a number"

    try:
        command = f"SET+{ch}+{atten}"
        result = await _execute_command(ip_address.strip(), command, username, password)
        return f"✅ Channel {ch} attenuation set to {atten} dB\n\n📡 Response: {result.strip()}"
    except httpx.HTTPStatusError as e:
        return f"❌ API Error: {e.response.status_code}"
    except Exception as e:
        logger.error(f"Error in set_attenuation: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def set_all_attenuation(ip_address: str = "", attenuations: str = "", username: str = "admin", password: str = "admin") -> str:
    """Set attenuation on all channels - single value for all or comma-separated per-channel values."""
    if not ip_address.strip():
        return "❌ Error: ip_address is required"
    if not attenuations.strip():
        return "❌ Error: attenuations value is required (single value or comma-separated per-channel)"

    try:
        values = [v.strip() for v in attenuations.strip().split(",")]
        parsed = [float(v) for v in values]
    except ValueError:
        return "❌ Error: all attenuation values must be numbers"

    try:
        params = "+".join(str(v) for v in parsed)
        command = f"SAA+{params}"
        result = await _execute_command(ip_address.strip(), command, username, password)
        if len(parsed) == 1:
            return f"✅ All channels set to {parsed[0]} dB\n\n📡 Response: {result.strip()}"
        else:
            channel_list = ", ".join(f"Ch{i+1}={v} dB" for i, v in enumerate(parsed))
            return f"✅ Channels set: {channel_list}\n\n📡 Response: {result.strip()}"
    except httpx.HTTPStatusError as e:
        return f"❌ API Error: {e.response.status_code}"
    except Exception as e:
        logger.error(f"Error in set_all_attenuation: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def ramp_channels(ip_address: str = "", directions: str = "", atten_start: str = "", atten_stop: str = "", step: str = "", dwell: str = "", username: str = "admin", password: str = "admin") -> str:
    """Ramp (fade) attenuation across channels - directions is comma-separated A/D/E for each of the 8 channels."""
    if not ip_address.strip():
        return "❌ Error: ip_address is required"
    if not directions.strip():
        return "❌ Error: directions is required (comma-separated A/D/E for 8 channels, e.g. 'A,A,A,A,D,D,D,D')"
    if not atten_start.strip() or not atten_stop.strip() or not step.strip() or not dwell.strip():
        return "❌ Error: atten_start, atten_stop, step, and dwell are all required"

    dir_list = [d.strip().upper() for d in directions.strip().split(",")]
    if len(dir_list) != 8:
        return f"❌ Error: exactly 8 direction values required (got {len(dir_list)}). Use A=Ascend, D=Descend, E=Exclude"

    for d in dir_list:
        if d not in ("A", "D", "E"):
            return f"❌ Error: invalid direction '{d}'. Use A=Ascend, D=Descend, E=Exclude"

    try:
        start_val = float(atten_start.strip())
        stop_val = float(atten_stop.strip())
        step_val = float(step.strip())
        dwell_val = int(dwell.strip())
    except ValueError:
        return "❌ Error: atten_start, atten_stop, step must be numbers; dwell must be an integer (ms)"

    if step_val <= 0:
        return "❌ Error: step must be greater than 0"

    # Calculate estimated duration
    num_steps = int((stop_val - start_val) / step_val)
    estimated_ms = abs(num_steps) * dwell_val
    estimated_sec = estimated_ms / 1000.0

    # Format decimal values with trailing .0
    start_fmt = f"{start_val:.2f}"
    stop_fmt = f"{stop_val:.2f}"
    step_fmt = f"{step_val:.2f}"

    dir_params = "+".join(dir_list)
    command = f"RAMP+{dir_params}+{start_fmt}+{stop_fmt}+{step_fmt}+{dwell_val}"

    ip = ip_address.strip()
    ascending = [i + 1 for i, d in enumerate(dir_list) if d == "A"]
    descending = [i + 1 for i, d in enumerate(dir_list) if d == "D"]
    excluded = [i + 1 for i, d in enumerate(dir_list) if d == "E"]

    try:
        # Pre-ramp STATUS check
        logger.info("Fetching pre-ramp STATUS")
        pre_status = await _execute_command(ip, "STATUS", username, password)

        # Execute RAMP (blocks until complete)
        logger.info(f"Starting RAMP, estimated duration: {estimated_sec:.1f}s")
        ramp_timeout = max(estimated_sec + 30, 60.0)
        ramp_result = await _execute_command(ip, command, username, password, timeout=ramp_timeout)

        # Post-ramp STATUS check
        logger.info("Fetching post-ramp STATUS")
        post_status = await _execute_command(ip, "STATUS", username, password)

        output = f"""✅ Ramp complete

⏱️ Estimated duration: {estimated_sec:.1f}s ({abs(num_steps)} steps × {dwell_val}ms dwell)
📊 Range: {start_fmt} dB → {stop_fmt} dB (step: {step_fmt} dB)

📡 Ascending channels: {ascending if ascending else 'None'}
📡 Descending channels: {descending if descending else 'None'}
📡 Excluded channels: {excluded if excluded else 'None'}

--- Pre-Ramp Status ---
{pre_status.strip()}

--- Ramp Response (first ~40 steps shown) ---
{ramp_result.strip()}

--- Post-Ramp Status ---
{post_status.strip()}"""
        return output
    except httpx.HTTPStatusError as e:
        return f"❌ API Error: {e.response.status_code}"
    except httpx.ReadTimeout:
        return f"❌ Error: Request timed out. The ramp may still be running on the device. Estimated duration was {estimated_sec:.1f}s."
    except Exception as e:
        logger.error(f"Error in ramp_channels: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def ramp_loop(ip_address: str = "", directions: str = "", atten_start: str = "", atten_stop: str = "", step: str = "", dwell: str = "", loops: str = "", dry_run: str = "false", username: str = "admin", password: str = "admin", ctx: Context = None) -> str:
    """Ramp channels back and forth in a loop - set dry_run=true to get time estimate without executing."""
    if not ip_address.strip():
        return "❌ Error: ip_address is required"
    if not directions.strip():
        return "❌ Error: directions is required (comma-separated A/D/E for 8 channels, e.g. 'A,A,A,A,D,D,D,D')"
    if not atten_start.strip() or not atten_stop.strip() or not step.strip() or not dwell.strip():
        return "❌ Error: atten_start, atten_stop, step, and dwell are all required"
    if not loops.strip():
        return "❌ Error: loops is required (number of back-and-forth cycles)"

    dir_list = [d.strip().upper() for d in directions.strip().split(",")]
    if len(dir_list) != 8:
        return f"❌ Error: exactly 8 direction values required (got {len(dir_list)}). Use A=Ascend, D=Descend, E=Exclude"

    for d in dir_list:
        if d not in ("A", "D", "E"):
            return f"❌ Error: invalid direction '{d}'. Use A=Ascend, D=Descend, E=Exclude"

    try:
        start_val = float(atten_start.strip())
        stop_val = float(atten_stop.strip())
        step_val = float(step.strip())
        dwell_val = int(dwell.strip())
        loop_count = int(loops.strip())
    except ValueError:
        return "❌ Error: atten_start, atten_stop, step must be numbers; dwell and loops must be integers"

    if step_val <= 0:
        return "❌ Error: step must be greater than 0"
    if loop_count <= 0:
        return "❌ Error: loops must be greater than 0"

    # Build forward and reverse direction lists
    flip = {"A": "D", "D": "A", "E": "E"}
    reverse_dir_list = [flip[d] for d in dir_list]

    # Calculate estimated duration per single ramp
    num_steps = int((stop_val - start_val) / step_val)
    ramp_ms = abs(num_steps) * dwell_val
    ramp_sec = ramp_ms / 1000.0
    total_ramps = loop_count * 2
    total_sec = ramp_sec * total_ramps
    ramp_timeout = max(ramp_sec + 30, 60.0)

    ip = ip_address.strip()
    ascending = [i + 1 for i, d in enumerate(dir_list) if d == "A"]
    descending = [i + 1 for i, d in enumerate(dir_list) if d == "D"]
    excluded = [i + 1 for i, d in enumerate(dir_list) if d == "E"]
    is_dry_run = dry_run.strip().lower() in ("true", "1", "yes")

    # Format decimal values
    start_fmt = f"{start_val:.2f}"
    stop_fmt = f"{stop_val:.2f}"
    step_fmt = f"{step_val:.2f}"

    if is_dry_run:
        total_min = total_sec / 60.0
        return f"""⏱️ Ramp loop estimate (dry run — nothing executed)

🔁 Loops: {loop_count} ({total_ramps} total ramps)
📊 Range: {start_fmt} dB → {stop_fmt} dB (step: {step_fmt} dB, dwell: {dwell_val}ms)
⏱️ Single ramp: {ramp_sec:.1f}s ({abs(num_steps)} steps × {dwell_val}ms)
⏱️ Total estimated: {total_sec:.1f}s ({total_min:.1f} min)

📡 Forward — Ascending: {ascending if ascending else 'None'}, Descending: {descending if descending else 'None'}
📡 Reverse — Ascending: {descending if descending else 'None'}, Descending: {ascending if ascending else 'None'}
📡 Excluded: {excluded if excluded else 'None'}"""

    pre_status = ""
    loop_results = []
    failed_phase = ""

    try:
        # Pre-loop STATUS
        logger.info("Fetching pre-loop STATUS")
        pre_status = await _execute_command(ip, "STATUS", username, password)

        for i in range(loop_count):
            # Forward ramp
            fwd_params = "+".join(dir_list)
            fwd_command = f"RAMP+{fwd_params}+{start_fmt}+{stop_fmt}+{step_fmt}+{dwell_val}"
            logger.info(f"Loop {i + 1}/{loop_count} - forward ramp")
            failed_phase = f"loop {i + 1}/{loop_count} forward ramp"
            fwd_result = await _execute_with_progress(ip, fwd_command, username, password, ramp_timeout, ctx, i * 2, total_ramps, f"Loop {i + 1}/{loop_count} — forward ramp")

            # Reverse ramp
            rev_params = "+".join(reverse_dir_list)
            rev_command = f"RAMP+{rev_params}+{start_fmt}+{stop_fmt}+{step_fmt}+{dwell_val}"
            logger.info(f"Loop {i + 1}/{loop_count} - reverse ramp")
            failed_phase = f"loop {i + 1}/{loop_count} reverse ramp"
            rev_result = await _execute_with_progress(ip, rev_command, username, password, ramp_timeout, ctx, i * 2 + 1, total_ramps, f"Loop {i + 1}/{loop_count} — reverse ramp")

            loop_results.append(f"--- Loop {i + 1}/{loop_count} Forward ---\n{fwd_result.strip()}\n\n--- Loop {i + 1}/{loop_count} Reverse ---\n{rev_result.strip()}")
            failed_phase = ""

        # Post-loop STATUS
        if ctx:
            await ctx.report_progress(total_ramps, total_ramps, "All loops complete, fetching final status")
        logger.info("Fetching post-loop STATUS")
        post_status = await _execute_command(ip, "STATUS", username, password)

        ramp_details = "\n\n".join(loop_results)
        return f"""✅ Ramp loop complete ({loop_count} loops)

⏱️ Estimated total duration: {total_sec:.1f}s ({total_ramps} ramps × {ramp_sec:.1f}s each)
📊 Range: {start_fmt} dB → {stop_fmt} dB (step: {step_fmt} dB, dwell: {dwell_val}ms)
🔁 Loops: {loop_count}

📡 Forward — Ascending: {ascending if ascending else 'None'}, Descending: {descending if descending else 'None'}
📡 Reverse — Ascending: {descending if descending else 'None'}, Descending: {ascending if ascending else 'None'}
📡 Excluded: {excluded if excluded else 'None'}

--- Pre-Loop Status ---
{pre_status.strip()}

{ramp_details}

--- Post-Loop Status ---
{post_status.strip()}"""

    except Exception as e:
        logger.error(f"Error in ramp_loop: {e}")
        completed = len(loop_results)
        ramp_details = "\n\n".join(loop_results) if loop_results else "None"
        error_type = "Timed out" if isinstance(e, httpx.ReadTimeout) else str(e)
        return f"""⚠️ Ramp loop failed during {failed_phase or 'setup'} — {completed}/{loop_count} loops completed

❌ Error: {error_type}
📊 Range: {start_fmt} dB → {stop_fmt} dB (step: {step_fmt} dB, dwell: {dwell_val}ms)

--- Pre-Loop Status ---
{pre_status.strip() if pre_status else 'Not captured'}

{ramp_details}

To resume, run again with loops="{loop_count - completed}" to complete the remaining cycles."""


@mcp.tool()
async def randomize_channel(ip_address: str = "", channel: str = "", atten_start: str = "", atten_stop: str = "", username: str = "admin", password: str = "admin") -> str:
    """Set a single channel to a random attenuation level between two limits."""
    if not ip_address.strip():
        return "❌ Error: ip_address is required"
    if not channel.strip():
        return "❌ Error: channel is required (1-8)"
    if not atten_start.strip() or not atten_stop.strip():
        return "❌ Error: atten_start and atten_stop are required"

    try:
        ch = int(channel.strip())
        start_val = float(atten_start.strip())
        stop_val = float(atten_stop.strip())
    except ValueError:
        return "❌ Error: channel must be an integer, atten_start/atten_stop must be numbers"

    try:
        command = f"RAND+{ch}+{start_val}+{stop_val}"
        result = await _execute_command(ip_address.strip(), command, username, password)
        return f"🎲 Channel {ch} set to random attenuation between {start_val} dB and {stop_val} dB\n\n📡 Response: {result.strip()}"
    except httpx.HTTPStatusError as e:
        return f"❌ API Error: {e.response.status_code}"
    except Exception as e:
        logger.error(f"Error in randomize_channel: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def randomize_all_channels(ip_address: str = "", atten_start: str = "", atten_stop: str = "", consistent: str = "0", username: str = "admin", password: str = "admin") -> str:
    """Set all channels to random attenuation between two limits - consistent=1 for same value, 0 for different."""
    if not ip_address.strip():
        return "❌ Error: ip_address is required"
    if not atten_start.strip() or not atten_stop.strip():
        return "❌ Error: atten_start and atten_stop are required"

    try:
        start_val = float(atten_start.strip())
        stop_val = float(atten_stop.strip())
        consist_val = int(consistent.strip()) if consistent.strip() else 0
    except ValueError:
        return "❌ Error: atten_start/atten_stop must be numbers, consistent must be 0 or 1"

    if consist_val not in (0, 1):
        return "❌ Error: consistent must be 0 (different random values) or 1 (same random value)"

    try:
        command = f"RANDALL+{start_val}+{stop_val}+{consist_val}"
        result = await _execute_command(ip_address.strip(), command, username, password)
        mode = "same random value" if consist_val == 1 else "different random values"
        return f"🎲 All channels set to {mode} between {start_val} dB and {stop_val} dB\n\n📡 Response: {result.strip()}"
    except httpx.HTTPStatusError as e:
        return f"❌ API Error: {e.response.status_code}"
    except Exception as e:
        logger.error(f"Error in randomize_all_channels: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def get_status(ip_address: str = "", username: str = "admin", password: str = "admin") -> str:
    """Get current attenuation levels for all channels on the AdauraRF attenuator."""
    if not ip_address.strip():
        return "❌ Error: ip_address is required"

    try:
        result = await _execute_command(ip_address.strip(), "STATUS", username, password)
        return f"📊 Channel Status:\n\n{result.strip()}"
    except httpx.HTTPStatusError as e:
        return f"❌ API Error: {e.response.status_code}"
    except Exception as e:
        logger.error(f"Error in get_status: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def get_device_info(ip_address: str = "", username: str = "admin", password: str = "admin") -> str:
    """Get device information from the AdauraRF attenuator (model, serial, firmware, network)."""
    if not ip_address.strip():
        return "❌ Error: ip_address is required"

    try:
        result = await _execute_command(ip_address.strip(), "INFO", username, password)
        return f"🔍 Device Info:\n\n{result.strip()}"
    except httpx.HTTPStatusError as e:
        return f"❌ API Error: {e.response.status_code}"
    except Exception as e:
        logger.error(f"Error in get_device_info: {e}")
        return f"❌ Error: {str(e)}"


# === SERVER STARTUP ===
if __name__ == "__main__":
    logger.info("Starting AdauraRF 8-Channel MCP server...")

    try:
        mcp.run(transport='stdio')
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
