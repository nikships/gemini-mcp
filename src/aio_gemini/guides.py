"""Offline, attributed excerpts of Google's official media prompting guides."""

import json
from importlib.resources import files
from typing import Literal, get_args

from pydantic import BaseModel

from aio_gemini.catalog import (
    DEFAULT_MODEL,
    ImageModel,
    MusicModel,
    OmniModel,
    SpeechModel,
    TranscribeModel,
)

AnalysisMedia = Literal["all", "image", "audio", "video", "document"]
GuideName = Literal["image", "video", "speech", "music", "transcription", "analysis"]


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
            "editing, use store=true and previous_interaction_id.",
            "Set google_search=true for search grounding; the Lite image model "
            "does not support it. Model choices and size limits come from "
            "list_media_models and the generate_image schema.",
            "Illustrative input/output images and SDK code are omitted. Open the "
            "source page to see those assets; prompt templates are preserved.",
        ],
    )


def _video_guide() -> PromptGuide:
    return _guide(
        "Omni video generation, editing, and extension",
        ["generate_video", "generate_omni"],
        list(get_args(OmniModel)),
        ["omni"],
        [
            "Both tools use Omni through Interactions, not Veo. Pass ordered "
            "reference inputs as media; image/video role tags belong in prompt.",
            "For stateful edits or extensions, create a stored turn with store=true "
            "and pass its id as previous_interaction_id on the next stored turn.",
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
            "custom_vocabulary, mode, diarization, and word_timestamps to steer ASR. "
            "Use analyze_media for open-ended questions about audio.",
            "MCP booleans diarization and word_timestamps map to Google's nested "
            "verbatim-mode configuration. Smart mode cannot use either feature.",
            "Custom vocabulary cannot be combined with diarization or word timestamps.",
            "For large recordings, call upload_file, poll get_file until ACTIVE, "
            "then pass the file uri and mime_type as audio.",
        ],
    )


def _analysis_guide(media_type: AnalysisMedia) -> PromptGuide:
    source_names = {
        "image": "image-understanding",
        "audio": "audio",
        "video": "video-understanding",
        "document": "document-processing",
    }
    selected = (
        list(source_names.values())
        if media_type == "all"
        else [source_names[media_type]]
    )
    return _guide(
        f"Media analysis ({media_type})",
        ["analyze_media"],
        [DEFAULT_MODEL],
        ["files", *selected],
        [
            "Supply prompt and media items typed image, audio, video, or document. "
            "Use transcribe_audio for dedicated speech recognition.",
            "analyze_media places media before the text prompt. The official "
            "image-understanding page recommends text first, while the Files guide "
            "recommends image first. Both are preserved without silently reconciling "
            "this documentation difference; the MCP does not expose ordering.",
            "Set processing to agentic or static on a video media item. For long "
            "work use background=true with store=true, then poll get_interaction. "
            "This MCP does not stream or accept stateless step_list histories.",
            "The Files guide mentions temperature and top-k tuning; analyze_media "
            "does not expose those parameters. max_output_tokens controls the "
            "output bound, not sampling.",
            "Local/base64 inputs share a 10 MiB MCP limit. For larger files use "
            "upload_file, poll get_file until ACTIVE, and pass uri and mime_type.",
            "Illustrative images are omitted. Examples referring to a pictured "
            "object require the corresponding image on the official source page.",
        ],
    )


def get_prompt_guide(
    guide: GuideName, media_type: AnalysisMedia = "all"
) -> PromptGuide:
    """Read Google's official prompting guide for one kind of media task.

    guide selects the topic: image (generate_image), video (generate_video and
    generate_omni), speech (generate_speech), music (generate_music),
    transcription (transcribe_audio), or analysis (analyze_media). media_type
    narrows the analysis guide to image, audio, video, or document and is ignored
    for other guides. Returns the full guide text in sources[].markdown, plus
    source URLs and attribution. Local near-verbatim snapshot; no API key,
    network request, or charges.
    """
    if guide == "analysis":
        return _analysis_guide(media_type)
    return {
        "image": _image_guide,
        "video": _video_guide,
        "speech": _speech_guide,
        "music": _music_guide,
        "transcription": _transcription_guide,
    }[guide]()
