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
        assert {
            "ping",
            "generate_text",
            "list_models",
            "list_media_models",
            "get_image_prompt_guide",
            "get_video_prompt_guide",
            "get_speech_prompt_guide",
            "get_music_prompt_guide",
            "get_transcription_guide",
            "get_media_analysis_guide",
            "generate_image",
            "generate_video",
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
        generation = next(tool for tool in tools if tool.name == "generate_text")
        assert "prompt" in generation.input_schema["required"]
        assert "previous_interaction_id" in generation.input_schema["properties"]
        assert generation.input_schema["properties"]["store"]["default"] is False
        assert {"id", "status", "text"} <= set(generation.output_schema["properties"])
        image = next(tool for tool in tools if tool.name == "generate_image")
        assert image.input_schema["properties"]["model"]["default"] == (
            "gemini-3.1-flash-image"
        )
        assert {"id", "status", "text", "outputs"} <= set(
            image.output_schema["properties"]
        )
        result = await client.call_tool("ping")
        assert result.data == {"status": "ok", "default_model": "stdio-test-model"}
        with pytest.raises(ToolError, match="Set GEMINI_API_KEY or GOOGLE_API_KEY"):
            await client.call_tool("generate_text", {"prompt": "Hello"})
        with pytest.raises(ToolError, match="Set GEMINI_API_KEY or GOOGLE_API_KEY"):
            await client.call_tool("list_models")
        for tool, arguments in (
            ("generate_image", {"prompt": "A landscape"}),
            ("generate_video", {"prompt": "A landscape"}),
            ("generate_speech", {"text": "Hello"}),
            ("generate_music", {"prompt": "Piano music"}),
        ):
            with pytest.raises(ToolError, match="Set GEMINI_API_KEY or GOOGLE_API_KEY"):
                await client.call_tool(tool, arguments)
        assert (await client.call_tool("list_media_models")).data["verified_on"]
        music_guide = await client.call_tool("get_music_prompt_guide")
        assert music_guide.structured_content["sources"][0]["url"].endswith(
            "/lyria-prompt-guide"
        )
        assert (
            "## Lyrics and vocals"
            in (music_guide.structured_content["sources"][0]["markdown"])
        )
        analysis = await client.call_tool(
            "get_media_analysis_guide", {"media_type": "document"}
        )
        assert len(analysis.structured_content["sources"]) == 2
        assert (await client.call_tool("ping")).data["status"] == "ok"
