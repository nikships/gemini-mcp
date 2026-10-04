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
        args = ["--directory", str(ROOT), "run", "--frozen", "aio-gemini-mcp"]
    else:
        command = sys.executable
        args = ["-m", "aio_gemini"]

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
        # Protocol-level ping exists only in handshake-era MCP.
        if mode == "legacy":
            await client.ping()
        tools = await client.list_tools()
        assert {
            "generate_text",
            "get_prompt_guide",
            "generate_image",
            "generate_omni",
            "transcribe_audio",
            "generate_speech",
            "generate_music",
            "analyze_media",
            "get_interaction",
            "cancel_interaction",
            "delete_interaction",
            "upload_file",
            "get_file",
            "list_files",
            "delete_file",
            "download_file",
        } == {tool.name for tool in tools}
        for tool in (
            "generate_text",
            "generate_image",
            "generate_omni",
            "transcribe_audio",
            "generate_speech",
            "generate_music",
            "analyze_media",
        ):
            tool_info = next(item for item in tools if item.name == tool)
            assert "store" not in tool_info.input_schema["properties"]
        generation = next(tool for tool in tools if tool.name == "generate_text")
        assert "prompt" in generation.input_schema["required"]
        assert "previous_interaction_id" in generation.input_schema["properties"]
        assert {"id", "status", "text"} <= set(generation.output_schema["properties"])
        image = next(tool for tool in tools if tool.name == "generate_image")
        assert image.input_schema["properties"]["model"]["default"] == (
            "gemini-3.1-flash-image"
        )
        assert {"id", "status", "text", "outputs"} <= set(
            image.output_schema["properties"]
        )
        with pytest.raises(ToolError, match="Set GEMINI_API_KEY or GOOGLE_API_KEY"):
            await client.call_tool("generate_text", {"prompt": "Hello"})
        for tool, arguments in (
            ("generate_image", {"prompt": "A landscape"}),
            ("generate_omni", {"prompt": "A landscape"}),
            ("generate_speech", {"text": "Hello"}),
            ("generate_music", {"prompt": "Piano music"}),
        ):
            with pytest.raises(ToolError, match="Set GEMINI_API_KEY or GOOGLE_API_KEY"):
                await client.call_tool(tool, arguments)
        music_guide = await client.call_tool("get_prompt_guide", {"guide": "music"})
        assert music_guide.structured_content["sources"][0]["url"].endswith(
            "/lyria-prompt-guide"
        )
        assert (
            "## Lyrics and vocals"
            in (music_guide.structured_content["sources"][0]["markdown"])
        )
        analysis = await client.call_tool(
            "get_prompt_guide", {"guide": "analysis", "media_type": "document"}
        )
        assert len(analysis.structured_content["sources"]) == 2
