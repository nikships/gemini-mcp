"""Offline, attributed excerpts of Google's official media prompting guides."""

import json
from importlib.resources import files
from typing import Literal, get_args

from pydantic import BaseModel

from aio_gemini.catalog import (
    ImageModel,
    MusicModel,
    OmniModel,
    SpeechModel,
    TranscribeModel,
)

GuideName = Literal["image", "video", "speech", "music", "transcription"]


class GuideSource(BaseModel):
    """Official wording, with its provenance and disclosed omissions."""

    title: str
    url: str
    sections: list[str]
    modifications: list[str]
    markdown: str


class PromptGuide(BaseModel):
    """A dated local snapshot, not a live lookup or generated summary."""

    title: str
    related_tools: list[str]
    models: list[str]
    retrieved_on: str
    sources: list[GuideSource]
    attribution: str
    license: str
    license_url: str
    mcp_notes: list[str]


def _guide(
    title: str,
    related_tools: list[str],
    models: list[str],
    source_names: list[str],
    notes: list[str],
) -> PromptGuide:
    resources = files("aio_gemini").joinpath("data", "guides")
    manifest = json.loads(
        resources.joinpath("sources.json").read_text(encoding="utf-8")
    )
    sources = []
    for name in source_names:
        source = manifest["sources"][name]
        sources.append(
            GuideSource(
                title=source["title"],
                url=source["url"],
                sections=source["sections"],
                modifications=source["modifications"],
                markdown=resources.joinpath(f"{name}.md").read_text(encoding="utf-8"),
            )
        )
    return PromptGuide(
        title=title,
        related_tools=related_tools,
        models=models,
        retrieved_on=manifest["retrieved_on"],
        sources=sources,
        attribution=manifest["attribution"],
        license=manifest["license"],
        license_url=manifest["license_url"],
        mcp_notes=notes,
    )


def _image_guide() -> PromptGuide:
    return _guide(
        "Image generation and editing",
        ["generate_image"],
        list(get_args(ImageModel)),
        ["image-generation"],
        [
            "Pass the prompt as prompt and reference images as media. For iterative "
            "editing, pass the returned interaction id as previous_interaction_id.",
            "Set google_search=true for search grounding; the Lite image model "
            "does not support it. Model choices and size limits are exposed in "
            "the generate_image schema.",
            "Illustrative input/output images and SDK code are omitted. Open the "
            "source page to see those assets; prompt templates are preserved.",
        ],
    )


def _video_guide() -> PromptGuide:
    return _guide(
        "Omni video generation, editing, and extension",
        ["generate_omni"],
        list(get_args(OmniModel)),
        ["omni"],
        [
            "Omni uses Interactions. Pass ordered reference inputs as media; "
            "image/video role tags belong in prompt.",
            "For stateful edits or extensions, pass the returned interaction id "
            "as previous_interaction_id on the next turn.",
            "Uploaded-video extension has separate duration, dialogue, and regional "
            "limits; see the source page's Extension constraints and guidelines.",
        ],
    )


def _speech_guide() -> PromptGuide:
    return _guide(
        "Speech generation (TTS)",
        ["generate_speech"],
        list(get_args(SpeechModel)),
        ["speech-generation"],
        [
            "text is spoken verbatim. Top-level style or each turns item's style "
            "maps to speech_metadata.style; momentary vocal tags remain in text.",
            "For two speakers, supply turns and exactly two speakers with distinct "
            "names. Reuse voice IDs for consistency.",
            "The official guide references Voice design, replication, and the "
            "Extended Voice Library. This MCP can use existing voice IDs but "
            "does not create, clone, or search voices.",
            "generate_speech is non-streaming. The voice-agent workflow describes "
            "application-level orchestration, not a Live API tool in this MCP.",
        ],
    )


def _music_guide() -> PromptGuide:
    return _guide(
        "Lyria music generation",
        ["generate_music"],
        list(get_args(MusicModel)),
        ["lyria-prompt-guide", "music-generation"],
        [
            "Pass musical directions and optional custom lyrics in prompt. Duration, "
            "BPM, key, and song structure are prompt instructions, not MCP fields.",
            "Use lyria-3.5 for full songs and WAV, or lyria-3-clip-preview for short "
            "MP3 clips. Up to ten images can be supplied as media.",
            "Lyria RealTime uses a separate WebSocket API. Its weighted-prompt and "
            "steering sections are omitted; this MCP implements batch generation only.",
        ],
    )


def _transcription_guide() -> PromptGuide:
    return _guide(
        "Audio transcription (ASR)",
        ["transcribe_audio"],
        list(get_args(TranscribeModel)),
        ["transcribe"],
        [
            "transcribe_audio has no prompt argument. Use language_codes, "
            "custom_vocabulary, mode, diarization, and word_timestamps to steer ASR.",
            "MCP booleans diarization and word_timestamps map to Google's nested "
            "verbatim-mode configuration. Smart mode cannot use either feature.",
            "Custom vocabulary cannot be combined with diarization or word timestamps.",
            "For large recordings, call upload_file, poll get_file until ACTIVE, "
            "then pass the file uri and mime_type as audio.",
        ],
    )


def get_prompt_guide(guide: GuideName) -> PromptGuide:
    """Read Google's official prompting guide for a media task.

    Returns the full guide text in sources[].markdown, plus source URLs and
    attribution. Offline near-verbatim snapshot; needs no API key.
    """
    return {
        "image": _image_guide,
        "video": _video_guide,
        "speech": _speech_guide,
        "music": _music_guide,
        "transcription": _transcription_guide,
    }[guide]()
