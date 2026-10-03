import asyncio
import base64
import json
import stat
from pathlib import Path

import httpx
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from google.genai import interactions
from pydantic import ValidationError

from gemini_mcp import catalog, media, server


def encoded(value: bytes) -> str:
    return base64.b64encode(value).decode()


def interaction(*blocks, status="completed", model=None, steps=None):
    return {
        "id": "media-id",
        "status": status,
        "model": model,
        "steps": steps or [{"type": "model_output", "content": list(blocks)}],
    }


@pytest.fixture
def api(sdk_transport):
    requests = []

    def install(response):
        def handle(request):
            requests.append(request)
            assert request.url.host == "generativelanguage.googleapis.com"
            assert "/interactions" in request.url.path
            return httpx.Response(200, json=response)

        sdk_transport(handle)
        return requests

    return install


def request_body(requests):
    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert requests[0].url.path.endswith("/interactions")
    body = json.loads(requests[0].content)
    assert body["stream"] is False
    assert "response_modalities" not in body
    assert "response_mime_type" not in body
    return body


async def test_image_real_sdk_keeps_every_output(api, tmp_path):
    image_path = tmp_path / "reference.png"
    image_path.write_bytes(b"reference")
    requests = api(
        interaction(
            {"type": "text", "text": "First"},
            {
                "type": "image",
                "mime_type": "image/png",
                "data": encoded(b"first-image"),
            },
            {"type": "text", "text": "Second"},
            {
                "type": "image",
                "mime_type": "image/jpeg",
                "data": encoded(b"second-image"),
            },
            model=catalog.DEFAULT_IMAGE_MODEL,
        )
    )
    result = await server.generate_image(
        "Edit these",
        media=[
            media.MediaInput(
                type="image",
                mime_type="image/png",
                path=str(image_path),
            )
        ],
        aspect_ratio="16:9",
        image_size="2K",
        google_search=True,
        previous_interaction_id="prior",
        store=True,
    )
    body = request_body(requests)
    assert body["model"] == "gemini-3.1-flash-image"
    assert body["input"][0]["content"][0]["data"] == encoded(b"reference")
    assert body["response_format"] == [
        {"type": "text"},
        {"type": "image", "aspect_ratio": "16:9", "image_size": "2K"},
    ]
    assert body["tools"] == [{"type": "google_search"}]
    assert body["previous_interaction_id"] == "prior"
    assert body["store"] is True
    assert result.text == "First\nSecond"
    assert [block.type for block in result.outputs] == [
        "text",
        "image",
        "text",
        "image",
    ]
    assert (
        await asyncio.to_thread(Path(result.outputs[1].path).read_bytes)
        == b"first-image"
    )
    assert (
        await asyncio.to_thread(Path(result.outputs[3].path).read_bytes)
        == b"second-image"
    )
    assert Path(result.outputs[1].path).suffix == ".png"
    assert Path(result.outputs[3].path).suffix == ".jpg"
    assert result.outputs[1].data is None
    assert (
        stat.S_IMODE(
            (await asyncio.to_thread(Path(result.outputs[1].path).stat)).st_mode
        )
        == 0o600
    )


@pytest.mark.parametrize("tool", [server.generate_video, server.generate_omni])
async def test_omni_real_sdk_all_modalities_and_uri(api, tool):
    uri = "https://generativelanguage.googleapis.com/v1beta/files/generated:download?alt=media"
    requests = api(
        interaction(
            {"type": "video", "mime_type": "video/mp4", "uri": uri},
            model=catalog.DEFAULT_OMNI_MODEL,
        )
    )
    references = [
        media.MediaInput(type=kind, mime_type=mime, uri=f"files/{kind}")
        for kind, mime in (
            ("image", "image/jpeg"),
            ("image", "image/png"),
            ("audio", "audio/mp3"),
            ("video", "video/mp4"),
        )
    ]
    result = await tool(
        "Continue the scene",
        media=references,
        aspect_ratio="9:16",
        resolution="4k",
        duration_seconds=8,
        task="extend",
        previous_interaction_id="prior",
        store=True,
    )
    body = request_body(requests)
    assert body["model"] == "gemini-omni-1.1-flash"
    assert [block["type"] for block in body["input"][0]["content"]] == [
        "image",
        "image",
        "audio",
        "video",
        "text",
    ]
    assert body["response_format"] == {
        "type": "video",
        "aspect_ratio": "9:16",
        "resolution": "4k",
        "duration": "8s",
        "delivery": "uri",
    }
    assert body["generation_config"] == {"video_config": {"task": "extend"}}
    assert result.outputs[0].uri == uri
    assert result.outputs[0].file_name == "files/generated"
    assert result.outputs[0].path is None


async def test_transcribe_real_sdk_annotations(api):
    annotation = {
        "type": "word_info",
        "text": "Hello",
        "speaker": "spk_1",
        "start_offset": "0.100s",
        "end_offset": "0.450s",
    }
    requests = api(
        interaction(
            {"type": "text", "text": "Hello", "annotations": [annotation]},
        )
    )
    result = await server.transcribe_audio(
        media.MediaInput(type="audio", mime_type="audio/mp3", uri="files/audio"),
        language_codes=["en-US"],
        diarization=True,
        word_timestamps=True,
    )
    body = request_body(requests)
    assert body["model"] == "gemini-3.5-transcribe"
    assert body["generation_config"] == {
        "transcription_config": {
            "language_codes": ["en-US"],
            "mode": {
                "type": "verbatim",
                "diarization_mode": "speaker",
                "timestamp_granularities": ["word"],
            },
        }
    }
    assert result.text == "Hello"
    assert result.outputs[0].annotations == [annotation]


async def test_smart_transcription_and_vocabulary(api):
    requests = api(interaction({"type": "text", "text": "Hello"}))
    await server.transcribe_audio(
        media.MediaInput(type="audio", mime_type="audio/wav", data=encoded(b"audio")),
        mode="smart",
        custom_vocabulary=["Gemini"],
        language_codes=[],
    )
    body = request_body(requests)
    assert body["generation_config"]["transcription_config"] == {
        "mode": "smart",
        "custom_vocabulary": ["Gemini"],
        "language_codes": [],
    }


async def test_tts_real_sdk_style_is_not_spoken_and_wav_unchanged(api):
    wav = b"RIFF-existing-wave-container"
    requests = api(
        interaction(
            {
                "type": "audio",
                "mime_type": "audio/wav",
                "data": encoded(wav),
                "sample_rate": 24000,
                "channels": 1,
            },
        )
    )
    result = await server.generate_speech(
        text="Hello <laugh>",
        style="warm and friendly",
        voice="Kore",
        language="en-US",
        include_inline_data=True,
    )
    body = request_body(requests)
    assert body["model"] == "gemini-3.8-flash-tts"
    assert body["input"] == [
        {
            "type": "user_input",
            "content": [
                {
                    "type": "text",
                    "text": "Hello <laugh>",
                    "annotations": [
                        {"type": "speech_metadata", "style": "warm and friendly"}
                    ],
                }
            ],
        }
    ]
    assert body["generation_config"]["speech_config"] == [
        {"voice": "Kore", "language": "en-US"},
    ]
    assert body["response_format"] == {"type": "audio", "mime_type": "audio/wav"}
    assert result.outputs[0].data == encoded(wav)
    assert result.outputs[0].sample_rate == 24000
    assert await asyncio.to_thread(Path(result.outputs[0].path).read_bytes) == wav


async def test_two_speaker_tts_real_sdk(api):
    requests = api(
        interaction(
            {"type": "audio", "mime_type": "audio/l16", "data": encoded(b"pcm")},
        )
    )
    result = await server.generate_speech(
        turns=[
            media.SpeechTurn(text="Hello", speaker="Joe", style="cheerful"),
            media.SpeechTurn(text="Hi", speaker="Jane"),
        ],
        speakers=[
            media.Speaker(speaker="Joe", voice="Puck"),
            media.Speaker(speaker="Jane", voice="Kore"),
        ],
        model="gemini-3.8-flash-lite-tts",
        mime_type="audio/l16",
        sample_rate=16000,
    )
    body = request_body(requests)
    assert body["generation_config"] == {
        "speech_config": {
            "speakers": [
                {"speaker": "Joe", "voice": "Puck"},
                {"speaker": "Jane", "voice": "Kore"},
            ]
        }
    }
    turns = body["input"][0]["content"]
    assert turns[0]["annotations"][0]["speaker"] == "Joe"
    assert turns[1]["annotations"][0]["speaker"] == "Jane"
    assert body["response_format"]["sample_rate"] == 16000
    assert Path(result.outputs[0].path).suffix == ".pcm"
    assert await asyncio.to_thread(Path(result.outputs[0].path).read_bytes) == b"pcm"


@pytest.mark.parametrize("model", ["lyria-3.5", "lyria-3-clip-preview"])
async def test_lyria_real_sdk_keeps_interleaved_lyrics(api, model):
    requests = api(
        interaction(
            {"type": "text", "text": "[Verse] Hello"},
            {"type": "audio", "mime_type": "audio/mp3", "data": encoded(b"music")},
            {"type": "text", "text": "[Chorus] World"},
        )
    )
    result = await server.generate_music(
        "A jazz song",
        model=model,
        media=[
            media.MediaInput(type="image", mime_type="image/jpeg", uri="files/image")
        ],
    )
    body = request_body(requests)
    assert body["model"] == model
    assert body["response_format"] == [
        {"type": "text"},
        {"type": "audio", "mime_type": "audio/mp3"},
    ]
    assert result.text == "[Verse] Hello\n[Chorus] World"
    assert await asyncio.to_thread(Path(result.outputs[1].path).read_bytes) == b"music"


async def test_analyze_real_sdk_processing_and_current_model(api, monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "old-text-override")
    requests = api(interaction({"type": "text", "text": "A lecture"}))
    result = await server.analyze_media(
        "Summarize",
        [
            media.MediaInput(
                type="video",
                mime_type="video/mp4",
                uri="files/video",
                processing="agentic",
            )
        ],
        system_instruction="Be brief",
    )
    body = request_body(requests)
    assert body["model"] == "gemini-3.8-flash"
    assert body["input"][0]["content"][0]["processing"] == "agentic"
    assert body["system_instruction"] == "Be brief"
    assert result.text == "A lecture"


@pytest.mark.parametrize(
    "status",
    [
        "in_progress",
        "queued",
        "requires_action",
        "incomplete",
        "failed",
        "cancelled",
    ],
)
async def test_background_status_never_claims_success(api, status):
    requests = api(interaction(status=status))
    result = await server.generate_video("A scene", store=True, background=True)
    body = request_body(requests)
    assert body["background"] is True
    assert body["store"] is True
    assert result.id == "media-id"
    assert result.status == status
    assert result.outputs == []
    assert result.text == ""


async def test_get_cancel_delete_interactions_real_sdk(sdk_transport, tmp_path):
    requests = []

    def handle(request):
        requests.append(request)
        if request.method == "DELETE":
            return httpx.Response(200, json={})
        if request.url.path.endswith("/cancel"):
            return httpx.Response(200, json=interaction(status="cancelled"))
        return httpx.Response(
            200,
            json=interaction(
                steps=[
                    {
                        "type": "user_input",
                        "content": [{"type": "text", "text": "private-input"}],
                    },
                    {
                        "type": "thought",
                        "summary": [{"type": "text", "text": "private-thought"}],
                    },
                    {
                        "type": "model_output",
                        "content": [
                            {
                                "type": "video",
                                "mime_type": "video/mp4",
                                "data": encoded(b"video"),
                            },
                            {"type": "text", "text": "Result"},
                        ],
                    },
                ]
            ),
        )

    sdk_transport(handle)
    result = await server.get_interaction("stored-id", output_directory=str(tmp_path))
    assert result.text == "Result"
    assert "private" not in result.model_dump_json()
    assert await asyncio.to_thread(Path(result.outputs[0].path).read_bytes) == b"video"
    assert (await server.cancel_interaction("stored-id")).status == "cancelled"
    assert await server.delete_interaction("stored-id") == {
        "id": "stored-id",
        "status": "deleted",
    }
    assert [(r.method, r.url.path) for r in requests] == [
        ("GET", "/v1beta/interactions/stored-id"),
        ("POST", "/v1beta/interactions/stored-id/cancel"),
        ("DELETE", "/v1beta/interactions/stored-id"),
    ]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"type": "image", "mime_type": "image/png"},
        {"type": "image", "mime_type": "image/png", "path": "relative.png"},
        {"type": "image", "mime_type": "image/png", "data": "%%"},
        {
            "type": "image",
            "mime_type": "image/png",
            "data": "data:image/png;base64,QQ==",
        },
        {"type": "image", "mime_type": "audio/mp3", "uri": "files/a"},
        {
            "type": "audio",
            "mime_type": "audio/mp3",
            "uri": " ",
        },
        {
            "type": "audio",
            "mime_type": "audio/mp3",
            "uri": "files/a",
            "processing": "agentic",
        },
        {"type": "image", "mime_type": "image/png", "data": "QQ==", "uri": "files/a"},
    ],
)
def test_media_input_validation(kwargs):
    with pytest.raises((ValidationError, ToolError)):
        media.MediaInput(**kwargs)


async def test_inline_bounds_and_empty_files(tmp_path, monkeypatch):
    monkeypatch.setattr(media, "MAX_INLINE_BYTES", 4)
    file = tmp_path / "large.png"
    file.write_bytes(b"12345")
    with pytest.raises(ToolError, match="exceeds"):
        await media.media_contents(
            [media.MediaInput(type="image", mime_type="image/png", path=str(file))],
            allowed={"image"},
        )
    file.write_bytes(b"")
    with pytest.raises(ToolError, match="empty"):
        await media.media_contents(
            [media.MediaInput(type="image", mime_type="image/png", path=str(file))],
            allowed={"image"},
        )
    item = media.MediaInput(type="image", mime_type="image/png", data=encoded(b"123"))
    with pytest.raises(ToolError, match="Total inline"):
        await media.media_contents([item, item], allowed={"image"})


async def test_output_files_never_overwrite_and_preserve_usage(tmp_path):
    response = interactions.Interaction.model_validate(
        {
            **interaction(
                {"type": "audio", "mime_type": "audio/mp3", "data": encoded(b"mp3")}
            ),
            "usage": {"total_tokens": 42},
        }
    )
    first = await media.media_result(response, tmp_path)
    second = await media.media_result(response, tmp_path)
    assert first.outputs[0].path != second.outputs[0].path
    assert first.usage["total_tokens"] == 42
    assert await asyncio.to_thread(Path(first.outputs[0].path).read_bytes) == b"mp3"


async def test_output_failure_is_redacted(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("sensitive-local-detail")

    monkeypatch.setattr(media.tempfile, "mkstemp", fail)
    response = interactions.Interaction.model_validate(
        interaction(
            {"type": "image", "mime_type": "image/png", "data": encoded(b"img")},
        )
    )
    with pytest.raises(ToolError, match="Could not save") as exc:
        await media.media_result(response, tmp_path)
    assert "sensitive-local-detail" not in str(exc.value)


@pytest.mark.parametrize(
    "tool, arguments",
    [
        ("generate_image", {"prompt": "x", "model": "gemini-2.5-flash-image"}),
        (
            "generate_image",
            {"prompt": "x", "model": "gemini-3.1-flash-lite-image", "image_size": "2K"},
        ),
        (
            "generate_image",
            {"prompt": "x", "model": "gemini-3-pro-image", "image_size": "512"},
        ),
        ("generate_video", {"prompt": "x", "model": "veo-3.1-generate-preview"}),
        ("generate_video", {"prompt": "x", "duration_seconds": 2}),
        ("generate_video", {"prompt": "x", "task": "extend"}),
        ("generate_video", {"prompt": "x", "task": "image_to_video"}),
        ("generate_video", {"prompt": "x", "background": True}),
        ("generate_video", {"prompt": "x", "previous_interaction_id": " "}),
        ("generate_video", {"prompt": "x", "output_directory": "relative"}),
        ("generate_speech", {"text": "x", "model": "gemini-3.1-flash-tts-preview"}),
        ("generate_speech", {}),
        ("generate_speech", {"text": "x", "turns": [{"text": "x"}]}),
        ("generate_speech", {"turns": [{"text": "x", "speaker": "Joe"}]}),
        ("generate_speech", {"text": " "}),
        ("generate_music", {"prompt": "x", "model": "lyria-3-pro-preview"}),
        (
            "generate_music",
            {"prompt": "x", "model": "lyria-3-clip-preview", "mime_type": "audio/wav"},
        ),
        ("generate_music", {"prompt": "x", "timeout_seconds": 0}),
        ("analyze_media", {"prompt": "x", "media": []}),
        (
            "transcribe_audio",
            {
                "audio": {
                    "type": "audio",
                    "mime_type": "audio/mp3",
                    "uri": "files/audio",
                },
                "mode": "smart",
                "diarization": True,
            },
        ),
        (
            "transcribe_audio",
            {
                "audio": {
                    "type": "audio",
                    "mime_type": "audio/mp3",
                    "uri": "files/audio",
                },
                "custom_vocabulary": ["Gemini"],
                "word_timestamps": True,
            },
        ),
        ("delete_file", {"name": "https://example.test/file"}),
        ("download_file", {"name": "files/../file"}),
    ],
)
async def test_invalid_requests_never_contact_google(sdk_transport, tool, arguments):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=interaction())

    sdk_transport(handle)
    async with Client(server.create_server()) as client:
        with pytest.raises(ToolError):
            await client.call_tool(tool, arguments)
    assert requests == []


def test_catalog_uses_current_models_only():
    snapshot = catalog.list_media_models()
    assert snapshot["verified_on"] == "2026-10-03"
    defaults = {entry["default"] for entry in snapshot["models"]}
    assert defaults == {
        "gemini-3.8-flash",
        "gemini-3.1-flash-image",
        "gemini-omni-1.1-flash",
        "gemini-3.5-transcribe",
        "gemini-3.8-flash-tts",
        "lyria-3.5",
    }
    assert all(entry["default"] in entry["models"] for entry in snapshot["models"])


@pytest.mark.parametrize(
    "tool, arguments, model",
    [
        ("generate_image", {"prompt": "A tree"}, "gemini-3.1-flash-image"),
        ("generate_video", {"prompt": "A scene"}, "gemini-omni-1.1-flash"),
        ("generate_omni", {"prompt": "A scene"}, "gemini-omni-1.1-flash"),
        ("generate_speech", {"text": "Hello"}, "gemini-3.8-flash-tts"),
        ("generate_music", {"prompt": "A jazz song"}, "lyria-3.5"),
        (
            "transcribe_audio",
            {
                "audio": {
                    "type": "audio",
                    "mime_type": "audio/mp3",
                    "uri": "files/audio",
                }
            },
            "gemini-3.5-transcribe",
        ),
        (
            "analyze_media",
            {
                "prompt": "Describe",
                "media": [{"type": "image", "mime_type": "image/png", "data": "QQ=="}],
            },
            "gemini-3.8-flash",
        ),
    ],
)
async def test_media_mcp_calls_validate_and_serialize(api, tool, arguments, model):
    requests = api(
        interaction(
            {"type": "text", "text": "Result"},
            model=model,
        )
    )
    async with Client(server.create_server()) as client:
        result = await client.call_tool(tool, arguments)
    assert result.data.id == "media-id"
    assert result.data.status == "completed"
    assert result.data.text == "Result"
    assert result.data.outputs[0].type == "text"
    assert request_body(requests)["model"] == model
