import shutil
import sys
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("entrypoint", ["uv", "module"])
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_real_stdio(entrypoint, mode):
    if entrypoint == "uv":
        command = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
        args = ["--directory", str(ROOT), "run", "--frozen", "gemini-mcp"]
    else:
        command = sys.executable
        args = ["-m", "gemini_mcp"]

    transport = StdioTransport(
        command=command,
        args=args,
        cwd=str(ROOT),
        env={
            "GEMINI_API_KEY": "",
            "GOOGLE_API_KEY": "",
            "GEMINI_MODEL": "stdio-test-model",
        },
    )
    async with Client(transport, timeout=10, init_timeout=20, mode=mode) as client:
        # Protocol-level ping exists only in handshake-era MCP. The ping tool
        # below is available in both current and legacy protocols.
        if mode == "legacy":
            await client.ping()
        tools = await client.list_tools()
        assert {tool.name for tool in tools} == {"ping", "generate_text", "list_models"}
        generation = next(tool for tool in tools if tool.name == "generate_text")
        assert "prompt" in generation.input_schema["required"]
        assert "previous_interaction_id" in generation.input_schema["properties"]
        assert generation.input_schema["properties"]["store"]["default"] is False
        assert {"id", "status", "text"} <= set(generation.output_schema["properties"])
        result = await client.call_tool("ping")
        assert result.data == {"status": "ok", "default_model": "stdio-test-model"}
        with pytest.raises(ToolError, match="Set GEMINI_API_KEY or GOOGLE_API_KEY"):
            await client.call_tool("generate_text", {"prompt": "Hello"})
        with pytest.raises(ToolError, match="Set GEMINI_API_KEY or GOOGLE_API_KEY"):
            await client.call_tool("list_models")
        assert (await client.call_tool("ping")).data["status"] == "ok"
