"""Current model choices verified against Google Developer Knowledge docs."""

from typing import Literal, get_args

DOCS_VERIFIED_ON = "2026-10-03"
DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_IMAGE_MODEL = "gemini-3.1-flash-image"
DEFAULT_OMNI_MODEL = "gemini-omni-1.1-flash"
DEFAULT_TRANSCRIBE_MODEL = "gemini-3.5-transcribe"
DEFAULT_TTS_MODEL = "gemini-3.8-flash-tts"
DEFAULT_MUSIC_MODEL = "lyria-3.5"

ImageModel = Literal[
    "gemini-3.1-flash-image", "gemini-3.1-flash-lite-image", "gemini-3-pro-image"
]
OmniModel = Literal["gemini-omni-1.1-flash"]
TranscribeModel = Literal["gemini-3.5-transcribe"]
SpeechModel = Literal["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts"]
MusicModel = Literal["lyria-3.5", "lyria-3-clip-preview"]


def list_media_models() -> dict[str, object]:
    """Return the documented current model catalog, without an API request.

    This is a dated documentation snapshot, not account-specific availability.
    No legacy model is used as a fallback. Use list_models for account access.
    """
    return {
        "verified_on": DOCS_VERIFIED_ON,
        "models": [
            {
                "tool": tool,
                "default": default,
                "models": models,
                "documentation": f"https://ai.google.dev/gemini-api/docs/{guide}",
            }
            for tool, default, models, guide in (
                ("analyze_media", DEFAULT_MODEL, [DEFAULT_MODEL], "models"),
                (
                    "generate_image",
                    DEFAULT_IMAGE_MODEL,
                    list(get_args(ImageModel)),
                    "image-generation",
                ),
                (
                    "generate_video / generate_omni",
                    DEFAULT_OMNI_MODEL,
                    list(get_args(OmniModel)),
                    "omni",
                ),
                (
                    "transcribe_audio",
                    DEFAULT_TRANSCRIBE_MODEL,
                    list(get_args(TranscribeModel)),
                    "transcribe",
                ),
                (
                    "generate_speech",
                    DEFAULT_TTS_MODEL,
                    list(get_args(SpeechModel)),
                    "speech-generation",
                ),
                (
                    "generate_music",
                    DEFAULT_MUSIC_MODEL,
                    list(get_args(MusicModel)),
                    "music-generation",
                ),
            )
        ],
        "separate_apis": [
            "Veo video generation",
            "Live audio and live transcription",
            "Lyria RealTime",
            "Voice design and voice replication",
        ],
    }
