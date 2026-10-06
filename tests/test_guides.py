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

GUIDE_NAMES = ("image", "video", "speech", "music", "transcription")
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


async def test_mcp_rejects_unknown_guide():
    async with Client(server.create_server()) as client:
        with pytest.raises(ToolError, match="guide"):
            await client.call_tool("get_prompt_guide", {"guide": "../other"})
