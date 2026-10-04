import hashlib
import json
import re
from importlib.resources import files
from unittest.mock import Mock

import httpx
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from aio_gemini import guides, server
from aio_gemini.catalog import list_media_models

GUIDE_NAMES = ("image", "video", "speech", "music", "transcription", "analysis")
RESOURCES = files("aio_gemini").joinpath("data", "guides")
MANIFEST = json.loads(RESOURCES.joinpath("sources.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    blocked = Mock(side_effect=AssertionError("Guides must not contact Google/network"))
    monkeypatch.setattr(server.genai, "Client", blocked)
    monkeypatch.setattr(httpx.Client, "request", blocked)
    monkeypatch.setattr(httpx.AsyncClient, "request", blocked)
    return blocked


@pytest.mark.parametrize("name", GUIDE_NAMES)
def test_guides_are_offline_attributed_and_current(
    name, offline, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    result = guides.get_prompt_guide(name)
    assert result.retrieved_on == "2026-10-03"
    assert result.license == "CC-BY-4.0"
    assert result.license_url == "https://creativecommons.org/licenses/by/4.0/"
    assert "shared by Google" in result.attribution
    assert result.mcp_notes
    catalog = list_media_models()["models"]
    for related_tool in result.related_tools:
        entry = next(item for item in catalog if related_tool in item["tool"])
        assert result.models == entry["models"]
    assert result.sources
    for source in result.sources:
        assert source.url.startswith("https://ai.google.dev/gemini-api/docs/")
        assert source.sections and source.modifications and source.markdown.strip()
    offline.assert_not_called()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("name", MANIFEST["sources"])
def test_snapshot_integrity_and_no_bundled_visual_or_sdk_assets(name):
    resource = RESOURCES.joinpath(f"{name}.md")
    markdown = resource.read_text(encoding="utf-8")
    metadata = MANIFEST["sources"][name]
    assert (
        hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        == (metadata["excerpt_sha256"])
    )
    assert re.fullmatch(r"[0-9a-f]{64}", metadata["document_sha256"])
    assert "![" not in markdown and "<img " not in markdown
    assert "### Python" not in markdown
    assert "client.interactions.create" not in markdown
    assert "generate_content" not in markdown


@pytest.mark.parametrize(
    ("name", "phrases"),
    [
        (
            "image-generation",
            [
                "#### 1. Photorealistic scenes",
                "#### 7. Grounding with Google Search",
                "#### 2. Inpainting (semantic masking)",
                "#### 7. Character consistency: 360 view",
                "Keep everything else in the image exactly the same,",
                '**Use "semantic negative prompts":**',
            ],
        ),
        (
            "omni",
            [
                "Continuous, unbroken handheld shot of a fluffy tabby cat",
                'include `"Keep everything else the same"`',
                "### Prompting the audio",
                "### Timing events",
                "### Prompts for extending a video",
                "[# Sources <FIRST_FRAME>@Image1] [# References <IMAGE_REF_0>@Image2]",
            ],
        ),
        (
            "speech-generation",
            [
                "strictly as a **verbatim transcript**",
                "### Style field versus inline tags",
                "### Backchannels and overlapping speech",
                "### Consistency across generations and what to avoid",
                "**Test plain TTS first:**",
                "`<short pause>`",
            ],
        ),
        (
            "lyria-prompt-guide",
            [
                "## Prompt fundamentals",
                "### Genre keywords",
                "### Instrument keywords",
                "## Song structure and timing",
                "### Using your own lyrics",
                "### Vocal delivery and singer profiles",
                "### Non-lyrical vocal effects",
                "## Musical parameters",
                "### Lyria 3.5 examples",
                "A 30-second lofi hip hop beat with dusty vinyl crackle",
            ],
        ),
        ("music-generation", ["**Iterate with Clip first.**", "**Use section tags.**"]),
        (
            "transcribe",
            [
                "BCP-47 language codes",
                "best results are typically achieved with up to 100 terms",
                "Smart transcription",
                "incompatible with `timestamp_granularities` and `diarization_mode`",
                "**Provide clean audio:**",
            ],
        ),
        (
            "files",
            [
                "### Be specific in your instructions",
                "### Add a few examples",
                "### Break it down step-by-step",
                "### Specify the output format",
                "### Put your image first for single-image prompts",
                "### Troubleshooting your multimodal prompt",
            ],
        ),
        (
            "image-understanding",
            ["Use clear, non-blurry images.", "*before* the image"],
        ),
        (
            "audio",
            ["Generate a transcript of the speech.", "Provide a transcript from 02:30"],
        ),
        (
            "video-understanding",
            [
                "### Choose a processing mode",
                "### Multi-turn video conversations",
                "What are the examples given at 00:05 and 00:10 supposed to show us?",
                "Include timestamps for salient moments.",
                "**Prompt placement**",
            ],
        ),
        (
            "document-processing",
            [
                "document vision ***only meaningfully understands PDFs***",
                "Rotate pages to the correct orientation before uploading.",
            ],
        ),
    ],
)
def test_official_examples_and_sections_preserved(name, phrases):
    markdown = RESOURCES.joinpath(f"{name}.md").read_text(encoding="utf-8")
    for phrase in phrases:
        assert phrase in markdown


def test_separate_api_scope_and_mcp_notes():
    music = guides.get_prompt_guide("music")
    assert "## Prompting Lyria RealTime" not in music.sources[0].markdown
    assert "WeightedPrompt" not in music.sources[0].markdown
    assert "`none " not in music.sources[0].markdown
    assert any("RealTime" in note for note in music.mcp_notes)
    speech = guides.get_prompt_guide("speech")
    assert any(
        "does not create, clone, or search voices" in n for n in speech.mcp_notes
    )
    transcription = guides.get_prompt_guide("transcription")
    assert any("no prompt argument" in n for n in transcription.mcp_notes)
    analysis = guides.get_prompt_guide("analysis")
    assert len(analysis.sources) == 5
    assert any("documentation difference" in n for n in analysis.mcp_notes)


@pytest.mark.parametrize("media_type", ["image", "audio", "video", "document"])
def test_analysis_modality_selection(media_type):
    guide = guides.get_prompt_guide("analysis", media_type)
    assert len(guide.sources) == 2
    assert guide.sources[0].url.endswith("/files")
    assert guide.sources[1].url.endswith(
        {
            "image": "/image-understanding",
            "audio": "/audio",
            "video": "/video-understanding",
            "document": "/document-processing",
        }[media_type]
    )


def test_results_do_not_share_mutable_state():
    guide = guides.get_prompt_guide("music")
    guide.sources[0].markdown = "changed"
    guide.sources.clear()
    guide.models.clear()
    assert len(guides.get_prompt_guide("music").sources) == 2
    assert guides.get_prompt_guide("music").models


async def test_mcp_guide_schema_annotations_and_result(offline):
    async with Client(server.create_server()) as client:
        tools = await client.list_tools()
        names = {item.name for item in tools}
        assert "get_prompt_guide" in names
        assert not {n for n in names if n.endswith(("_prompt_guide", "_guide"))} - {
            "get_prompt_guide"
        }
        discovered = next(item for item in tools if item.name == "get_prompt_guide")
        assert discovered.annotations.read_only_hint is True
        assert discovered.annotations.destructive_hint is False
        assert discovered.annotations.idempotent_hint is True
        assert discovered.annotations.open_world_hint is False
        assert discovered.input_schema["required"] == ["guide"]
        assert set(discovered.input_schema["properties"]["guide"]["enum"]) == set(
            GUIDE_NAMES
        )
        assert {"sources", "attribution", "mcp_notes", "retrieved_on"} <= set(
            discovered.output_schema["properties"]
        )
        for name in GUIDE_NAMES:
            result = await client.call_tool("get_prompt_guide", {"guide": name})
            assert result.structured_content == (
                guides.get_prompt_guide(name).model_dump()
            )
    offline.assert_not_called()


async def test_mcp_analysis_enum_and_invalid_selection():
    async with Client(server.create_server()) as client:
        tool = next(
            item
            for item in await client.list_tools()
            if item.name == "get_prompt_guide"
        )
        selection = tool.input_schema["properties"]["media_type"]
        assert selection["default"] == "all"
        assert set(selection["enum"]) == {"all", "image", "audio", "video", "document"}
        with pytest.raises(ToolError, match="guide"):
            await client.call_tool("get_prompt_guide", {"guide": "../other"})
        with pytest.raises(ToolError, match="media_type"):
            await client.call_tool(
                "get_prompt_guide", {"guide": "analysis", "media_type": "../other"}
            )
        result = await client.call_tool(
            "get_prompt_guide", {"guide": "analysis", "media_type": "audio"}
        )
        assert result.structured_content == (
            guides.get_prompt_guide("analysis", "audio").model_dump()
        )


def test_media_type_is_ignored_for_other_guides():
    assert (
        guides.get_prompt_guide("music", "audio").model_dump()
        == guides.get_prompt_guide("music").model_dump()
    )
