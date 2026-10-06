"""Keep stdout exclusively for the MCP protocol."""

import asyncio
import os
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from google import genai
from google.genai import errors, types
from google.genai._gaos.lib import compat_errors as interaction_errors
from pydantic import BaseModel, Field

from aio_gemini.catalog import (
    DEFAULT_IMAGE_MODEL,
    DEFAULT_MUSIC_MODEL,
    DEFAULT_OMNI_MODEL,
    DEFAULT_TRANSCRIBE_MODEL,
    DEFAULT_TTS_MODEL,
    ImageModel,
    MusicModel,
    OmniModel,
    SpeechModel,
    TranscribeModel,
)
from aio_gemini.guides import get_prompt_guide
from aio_gemini.media import (
    Delivery,
    ImageAspectRatio,
    MediaInput,
    MediaResult,
    NonBlank,
    Speaker,
    SpeechMimeType,
    SpeechTurn,
    VideoAspectRatio,
    VideoResolution,
    VideoTask,
    local_file,
    media_contents,
    media_output_file,
    media_result,
)
from aio_gemini.media import (
    output_directory as resolve_output_directory,
)

Timeout = Annotated[int, Field(ge=1, le=1800)]
MediaList = Annotated[list[MediaInput], Field(max_length=20)]


@asynccontextmanager
async def _google_client(
    timeout_seconds: int = 60,
) -> AsyncIterator[genai.client.AsyncClient]:
    key = (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
    )
    if not key:
        raise ToolError("Set GEMINI_API_KEY or GOOGLE_API_KEY to use Google AI tools.")

    try:
        # Close both SDK clients, including when a request fails or is cancelled.
        with genai.Client(
            api_key=key,
            vertexai=False,
            enterprise=False,
            http_options=types.HttpOptions(
                timeout=timeout_seconds * 1000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        ) as client:
            async with client.aio as async_client:
                # google-genai 2.28's Interactions adapter interprets attempts=1
                # as one extra retry, unlike Files. Disable its retry strategy
                # explicitly to avoid duplicating generation jobs and charges.
                async_client.interactions.sdk_configuration.retry_config.strategy = (
                    "none"
                )
                yield async_client
    except interaction_errors.APIConnectionError, httpx.RequestError:
        raise ToolError(
            "Could not reach Google Gen AI. Check your network and try again."
        ) from None
    except interaction_errors.APIError as exc:
        # Interactions currently uses a separate SDK error hierarchy.
        status = f" (HTTP {exc.status_code})" if exc.status_code is not None else ""
        raise ToolError(
            f"Google Interactions request failed{status}. "
            "Check your API key, model access, and quota."
        ) from None
    except errors.APIError as exc:
        # Upstream messages and URLs may contain credentials or submitted content.
        raise ToolError(
            f"Google Gen AI request failed (HTTP {exc.code}). "
            "Check your API key, model access, and quota."
        ) from None


def _not_blank(value: str, name: str) -> str:
    if not value.strip():
        raise ToolError(f"{name} must not be blank.")
    return value


async def _create_media(
    *,
    model: str,
    input: Any,
    response_format: Any = None,
    generation_config: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
    system_instruction: str | None = None,
    previous_interaction_id: str | None = None,
    background: bool = False,
    timeout_seconds: int = 600,
    output_directory_path: str | None = None,
    include_inline_data: bool = False,
) -> MediaResult:
    if previous_interaction_id is not None:
        previous_interaction_id = _not_blank(
            previous_interaction_id, "previous_interaction_id"
        ).strip()
    directory = resolve_output_directory(output_directory_path)
    async with _google_client(timeout_seconds) as client:
        response = await client.interactions.create(
            model=model,
            input=input,
            response_format=response_format,
            generation_config=generation_config,
            tools=tools,
            system_instruction=system_instruction,
            previous_interaction_id=previous_interaction_id,
            store=True,
            background=background,
            stream=False,
            timeout=timeout_seconds,
        )
    return await media_result(
        response, directory, include_inline_data=include_inline_data
    )


async def generate_image(
    prompt: NonBlank,
    media: MediaList | None = None,
    model: ImageModel = DEFAULT_IMAGE_MODEL,
    aspect_ratio: ImageAspectRatio | None = None,
    image_size: Literal["512", "1K", "2K", "4K"] = "1K",
    include_text: bool = True,
    google_search: bool = False,
    previous_interaction_id: NonBlank | None = None,
    background: bool = False,
    timeout_seconds: Timeout = 600,
    output_directory: NonBlank | None = None,
    include_inline_data: bool = False,
) -> MediaResult:
    """Generate or edit images with Nano Banana.

    Supply reference images, videos, or PDFs, or continue a stored interaction.
    Lite supports only 1K and no Google Search.
    """
    _not_blank(prompt, "prompt")
    if model == "gemini-3.1-flash-lite-image":
        if image_size != "1K" or google_search:
            raise ToolError("Nano Banana 2 Lite supports only 1K and no Google Search.")
    if model == "gemini-3-pro-image" and image_size == "512":
        raise ToolError("Nano Banana Pro supports 1K, 2K, or 4K, not 512.")
    if sum(item.type == "image" for item in media or []) > 14:
        raise ToolError("Image generation supports at most 14 reference images.")
    contents = await media_contents(media, allowed={"image", "video", "document"})
    contents.append({"type": "text", "text": prompt})
    image_format = {"type": "image", "image_size": image_size}
    if aspect_ratio is not None:
        image_format["aspect_ratio"] = aspect_ratio
    # Search declarations are scoped to each interaction, including edit turns.
    return await _create_media(
        tools=[{"type": "google_search"}] if google_search else None,
        model=model,
        input=contents,
        response_format=[{"type": "text"}, image_format]
        if include_text
        else image_format,
        previous_interaction_id=previous_interaction_id,
        background=background,
        timeout_seconds=timeout_seconds,
        output_directory_path=output_directory,
        include_inline_data=include_inline_data,
    )


async def generate_omni(
    prompt: NonBlank,
    media: MediaList | None = None,
    model: OmniModel = DEFAULT_OMNI_MODEL,
    aspect_ratio: VideoAspectRatio | None = None,
    resolution: VideoResolution = "720p",
    duration_seconds: Annotated[int | None, Field(ge=3, le=10)] = None,
    task: VideoTask | None = None,
    delivery: Delivery = "uri",
    previous_interaction_id: NonBlank | None = None,
    background: bool = False,
    timeout_seconds: Timeout = 600,
    output_directory: NonBlank | None = None,
    include_inline_data: bool = False,
) -> MediaResult:
    """Generate, edit, interpolate, or extend video with Omni.

    Two ordered images can be first/last frames when described in the prompt.
    Prefer prompt-based edits and extension; task applies strict constraints.
    Delivery defaults to uri (Google Files) or may be set to inline.
    """
    _not_blank(prompt, "prompt")
    contents = await media_contents(media, allowed={"image", "audio", "video"})
    if task in {"edit", "extend"} and not (
        previous_interaction_id or any(item["type"] == "video" for item in contents)
    ):
        raise ToolError("edit/extend requires a video or previous_interaction_id.")
    if task in {"image_to_video", "reference_to_video"} and not any(
        item["type"] == "image" for item in contents
    ):
        raise ToolError("image_to_video/reference_to_video requires an image.")
    contents.append({"type": "text", "text": prompt})
    format: dict[str, Any] = {
        "type": "video",
        "resolution": resolution,
        "delivery": delivery,
    }
    if aspect_ratio is not None:
        format["aspect_ratio"] = aspect_ratio
    if duration_seconds is not None:
        format["duration"] = f"{duration_seconds}s"
    return await _create_media(
        model=model,
        input=contents,
        response_format=format,
        generation_config={"video_config": {"task": task}} if task else None,
        previous_interaction_id=previous_interaction_id,
        background=background,
        timeout_seconds=timeout_seconds,
        output_directory_path=output_directory,
        include_inline_data=include_inline_data,
    )


async def transcribe_audio(
    audio: MediaInput,
    model: TranscribeModel = DEFAULT_TRANSCRIBE_MODEL,
    mode: Literal["verbatim", "smart"] = "verbatim",
    language_codes: list[NonBlank] | None = None,
    custom_vocabulary: Annotated[list[NonBlank] | None, Field(max_length=1000)] = None,
    diarization: bool = False,
    word_timestamps: bool = False,
    background: bool = False,
    timeout_seconds: Timeout = 600,
) -> MediaResult:
    """Transcribe audio.

    Returns text and ordered blocks containing word_info annotations. Smart
    mode cannot use diarization/timestamps; vocabulary cannot use either.
    Language detection is automatic when language_codes is omitted or empty.
    Upload long recordings first.
    """
    if mode == "smart" and (diarization or word_timestamps):
        raise ToolError(
            "Smart transcription cannot use diarization or word timestamps."
        )
    if custom_vocabulary and (diarization or word_timestamps):
        raise ToolError("Custom vocabulary cannot use diarization or word timestamps.")
    for value in (language_codes or []) + (custom_vocabulary or []):
        _not_blank(value, "language_codes/custom_vocabulary")
    config: dict[str, Any] = {
        "mode": "smart" if mode == "smart" else {"type": "verbatim"},
    }
    if mode == "verbatim":
        if diarization:
            config["mode"]["diarization_mode"] = "speaker"
        if word_timestamps:
            config["mode"]["timestamp_granularities"] = ["word"]
    if language_codes is not None:
        config["language_codes"] = language_codes
    if custom_vocabulary is not None:
        config["custom_vocabulary"] = custom_vocabulary
    return await _create_media(
        model=model,
        input=await media_contents([audio], allowed={"audio"}),
        generation_config={"transcription_config": config},
        background=background,
        timeout_seconds=timeout_seconds,
    )


async def generate_speech(
    text: NonBlank | None = None,
    turns: Annotated[list[SpeechTurn] | None, Field(min_length=1)] = None,
    voice: NonBlank = "Kore",
    style: str | None = None,
    language: NonBlank | None = None,
    speakers: Annotated[list[Speaker] | None, Field(min_length=2, max_length=2)] = None,
    model: SpeechModel = DEFAULT_TTS_MODEL,
    mime_type: SpeechMimeType = "audio/wav",
    sample_rate: Annotated[int | None, Field(gt=0)] = None,
    previous_interaction_id: NonBlank | None = None,
    background: bool = False,
    timeout_seconds: Timeout = 600,
    output_directory: NonBlank | None = None,
    include_inline_data: bool = False,
) -> MediaResult:
    """Generate single- or two-speaker TTS.

    Supply text OR structured turns. Text is spoken verbatim, so put delivery
    instructions in style, not text. Multi-speaker turns must name a configured
    speaker. Accepts prebuilt or existing custom voice IDs.
    """
    if (text is None) == (turns is None):
        raise ToolError("Provide exactly one of text or turns.")
    _not_blank(voice, "voice")
    if language is not None:
        _not_blank(language, "language")
    if text is not None:
        _not_blank(text, "text")
        turns = [SpeechTurn(text=text, style=style)]
    if not turns:
        raise ToolError("turns must not be empty.")
    if speakers is not None:
        if language is not None:
            raise ToolError("For multi-speaker speech, set language on each speaker.")
        names = {speaker.speaker for speaker in speakers}
        if len(speakers) != 2 or len(names) != 2:
            raise ToolError("Provide exactly two speakers with distinct names.")
        if any(turn.speaker not in names for turn in turns):
            raise ToolError("Every turn must name one of the configured speakers.")
        speech_config: Any = {
            "speakers": [speaker.model_dump(exclude_none=True) for speaker in speakers]
        }
    else:
        if any(turn.speaker is not None for turn in turns):
            raise ToolError("Named turns require speakers configuration.")
        speech_config = [{"voice": voice}]
        if language is not None:
            speech_config[0]["language"] = language
    contents = []
    for turn in turns:
        annotation: dict[str, Any] = {"type": "speech_metadata"}
        if turn.speaker is not None:
            annotation["speaker"] = turn.speaker
        delivery_style = turn.style if turn.style is not None else style
        if delivery_style is not None:
            annotation["style"] = delivery_style
        contents.append(
            {
                "type": "text",
                "text": turn.text,
                "annotations": [annotation],
            }
        )
    format: dict[str, Any] = {"type": "audio", "mime_type": mime_type}
    if sample_rate is not None:
        format["sample_rate"] = sample_rate
    return await _create_media(
        model=model,
        input=[{"type": "user_input", "content": contents}],
        response_format=format,
        generation_config={"speech_config": speech_config},
        previous_interaction_id=previous_interaction_id,
        background=background,
        timeout_seconds=timeout_seconds,
        output_directory_path=output_directory,
        include_inline_data=include_inline_data,
    )


async def generate_music(
    prompt: NonBlank,
    media: Annotated[list[MediaInput] | None, Field(max_length=10)] = None,
    model: MusicModel = DEFAULT_MUSIC_MODEL,
    mime_type: Literal["audio/mp3", "audio/wav"] = "audio/mp3",
    include_text: bool = True,
    background: bool = False,
    timeout_seconds: Timeout = 600,
    output_directory: NonBlank | None = None,
    include_inline_data: bool = False,
) -> MediaResult:
    """Generate music with Lyria.

    Lyria 3.5 creates full songs; Clip is the short-clip specialist. Up to ten
    images can inspire music. MP3 is default; WAV is supported only by Lyria 3.5.
    """
    _not_blank(prompt, "prompt")
    if model == "lyria-3-clip-preview" and mime_type != "audio/mp3":
        raise ToolError("Lyria Clip supports MP3; use Lyria 3.5 for WAV.")
    contents = await media_contents(media, allowed={"image"})
    contents.append({"type": "text", "text": prompt})
    audio_format = {"type": "audio", "mime_type": mime_type}
    return await _create_media(
        model=model,
        input=contents,
        response_format=[{"type": "text"}, audio_format]
        if include_text
        else audio_format,
        background=background,
        timeout_seconds=timeout_seconds,
        output_directory_path=output_directory,
        include_inline_data=include_inline_data,
    )


async def get_interaction(
    interaction_id: NonBlank,
    output_directory: NonBlank | None = None,
    include_inline_data: bool = False,
) -> MediaResult:
    """Retrieve or poll a stored interaction and save any inline outputs.

    Repeated retrieval of inline outputs creates new unique local files.
    """
    id = _not_blank(interaction_id, "interaction_id").strip()
    directory = resolve_output_directory(output_directory)
    async with _google_client() as client:
        response = await client.interactions.get(id, stream=False, timeout=60)
    return await media_result(
        response, directory, include_inline_data=include_inline_data
    )


async def cancel_interaction(interaction_id: NonBlank) -> MediaResult:
    """Cancel a running background interaction."""
    id = _not_blank(interaction_id, "interaction_id").strip()
    async with _google_client() as client:
        response = await client.interactions.cancel(id, timeout=60)
    return await media_result(response, resolve_output_directory(None))


async def delete_interaction(interaction_id: NonBlank) -> dict[str, str]:
    """Delete a stored interaction from Google; local outputs are untouched."""
    id = _not_blank(interaction_id, "interaction_id").strip()
    async with _google_client() as client:
        await client.interactions.delete(id, timeout=60)
    return {"id": id, "status": "deleted"}


class FileResult(BaseModel):
    name: str
    uri: str
    mime_type: str
    state: str
    display_name: str | None = None
    size_bytes: int | None = None
    expiration_time: str | None = None


def _file_result(file: types.File) -> FileResult:
    return FileResult(
        name=file.name or "",
        uri=file.uri or "",
        mime_type=file.mime_type or "",
        state=file.state.value if file.state else "UNKNOWN",
        display_name=file.display_name,
        size_bytes=file.size_bytes,
        expiration_time=file.expiration_time.isoformat()
        if file.expiration_time
        else None,
    )


async def upload_file(
    path: NonBlank,
    mime_type: NonBlank,
    display_name: NonBlank | None = None,
    timeout_seconds: Timeout = 600,
) -> FileResult:
    """Upload a local file to Google Files for reuse as media input.

    Poll get_file until ACTIVE before using the uri in an interaction. Uploads
    expire after 48 hours.
    """
    file = await asyncio.to_thread(local_file, path)
    _not_blank(mime_type, "mime_type")
    if display_name is not None:
        _not_blank(display_name, "display_name")
    try:
        async with _google_client(timeout_seconds) as client:
            uploaded = await client.files.upload(
                file=file,
                config=types.UploadFileConfig(
                    mime_type=mime_type, display_name=display_name
                ),
            )
    except OSError:
        raise ToolError("Could not read the local media file for upload.") from None
    return _file_result(uploaded)


def _file_name(name: str) -> str:
    name = _not_blank(name, "name").strip()
    if not re.fullmatch(r"files/[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?", name):
        raise ToolError("name must be a Google Files resource name: files/FILE_ID.")
    return name


async def get_file(name: NonBlank) -> FileResult:
    """Check an uploaded Google file's readiness, URI, and expiration."""
    name = _file_name(name)
    async with _google_client() as client:
        return _file_result(await client.files.get(name=name))


async def list_files(
    limit: Annotated[int, Field(ge=1, le=1000)] = 100,
) -> list[FileResult]:
    """List uploaded Google files with their processing state."""
    async with _google_client() as client:
        pager = await client.files.list(config={"page_size": min(limit, 100)})
        files = []
        async for file in pager:
            files.append(_file_result(file))
            if len(files) >= limit:
                break
        return files


async def delete_file(name: NonBlank) -> dict[str, str]:
    """Delete an uploaded Google file; local files are untouched."""
    name = _file_name(name)
    async with _google_client() as client:
        await client.files.delete(name=name)
    return {"name": name, "status": "deleted"}


async def download_file(
    name: NonBlank,
    output_directory: NonBlank | None = None,
    timeout_seconds: Timeout = 600,
) -> dict[str, str]:
    """Download a generated Google file to a unique local file.

    Use file_name from URI media output. Only ACTIVE generated files are
    downloadable, not uploaded ones. Poll get_file for PROCESSING files, then retry.
    """
    name = _file_name(name)
    directory = resolve_output_directory(output_directory)
    async with _google_client(timeout_seconds) as client:
        file = await client.files.get(name=name)
        if file.state != types.FileState.ACTIVE:
            raise ToolError("File is not ACTIVE. Check get_file before downloading.")
        if not file.download_uri:
            raise ToolError("Only generated Google files are downloadable.")
        with media_output_file(directory, "download", file.mime_type) as (output, path):
            await client.files.download(file=file, destination=output)
    return {"name": name, "path": path, "mime_type": file.mime_type or ""}


def create_server() -> FastMCP:
    server = FastMCP(
        "Gemini",
        instructions=(
            "Google Interactions API tools. REQUIRED: before your first call to any "
            "media tool in a session, read the matching get_prompt_guide guide in "
            "full. Do not prompt from memory. Guides are free and offline. "
            "Media tools use documented current models only, "
            "and save inline output to local files; URI output is not downloaded. "
            "Generation returns id, status, text, and ordered media outputs. "
            "Poll background work with get_interaction. Upload large input with "
            "upload_file, "
            "poll get_file until ACTIVE, then pass its uri and mime_type."
        ),
        mask_error_details=True,
    )
    for tool in (
        generate_image,
        generate_omni,
        transcribe_audio,
        generate_speech,
        generate_music,
        get_interaction,
        cancel_interaction,
        delete_interaction,
        upload_file,
        get_file,
        list_files,
        delete_file,
        download_file,
    ):
        server.tool(tool)
    server.tool(
        get_prompt_guide,
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    return server


mcp = create_server()


def main() -> None:
    """Run locally over stdin/stdout, without opening a network listener."""
    mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
