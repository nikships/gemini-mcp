"""Validated media inputs and lossless model-output extraction."""

import asyncio
import base64
import binascii
import os
import re
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Annotated, Any, Literal, Self
from urllib.parse import urlsplit

from fastmcp.exceptions import ToolError
from google.genai import interactions
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NonBlank = Annotated[str, Field(min_length=1)]
MediaType = Literal["image", "audio", "video", "document"]
ImageAspectRatio = Literal[
    "1:1",
    "2:3",
    "3:2",
    "3:4",
    "4:3",
    "4:5",
    "5:4",
    "9:16",
    "16:9",
    "21:9",
    "1:8",
    "8:1",
    "1:4",
    "4:1",
]
VideoAspectRatio = Literal["16:9", "9:16"]
VideoResolution = Literal["360p", "720p", "1080p", "4k"]
VideoTask = Literal[
    "text_to_video", "image_to_video", "reference_to_video", "edit", "extend"
]
Delivery = Literal["inline", "uri"]
SpeechMimeType = Literal["audio/wav", "audio/l16", "audio/mulaw", "audio/alaw"]

# A server-side memory bound, not Google's upload or model limit.
MAX_INLINE_BYTES = 10 * 1024 * 1024
MAX_BASE64_LENGTH = ((MAX_INLINE_BYTES + 2) // 3) * 4


class MediaInput(BaseModel):
    """Provide exactly one absolute local path, base64 payload, or Google URI.

    Local paths/base64 are limited to 10 MiB total per request. Use upload_file
    and uri for larger media. URI inputs are passed to Google, never fetched here.
    """

    model_config = ConfigDict(extra="forbid")
    type: MediaType
    mime_type: NonBlank
    path: NonBlank | None = None
    data: Annotated[str, Field(min_length=1, max_length=MAX_BASE64_LENGTH)] | None = (
        None
    )
    uri: NonBlank | None = None

    @field_validator("mime_type", "path", "uri")
    @classmethod
    def not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def check_source(self) -> Self:
        if sum(source is not None for source in (self.path, self.data, self.uri)) != 1:
            raise ValueError("Provide exactly one of path, data, or uri.")
        if self.path is not None and not Path(self.path).is_absolute():
            raise ValueError("path must be absolute.")
        prefix = "application/" if self.type == "document" else f"{self.type}/"
        if not self.mime_type.startswith(prefix):
            raise ValueError("mime_type must match the media type.")
        if self.data is not None:
            decode_media(self.data, limit=MAX_INLINE_BYTES)
        return self


class SpeechTurn(BaseModel):
    """A verbatim transcript turn, with instructions separate from speech."""

    model_config = ConfigDict(extra="forbid")
    text: NonBlank
    speaker: NonBlank | None = None
    style: str | None = None

    @field_validator("text", "speaker")
    @classmethod
    def not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


class Speaker(BaseModel):
    model_config = ConfigDict(extra="forbid")
    speaker: NonBlank
    voice: NonBlank
    language: NonBlank | None = None

    @field_validator("speaker", "voice", "language")
    @classmethod
    def not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


class OutputContent(BaseModel):
    """An ordered output block. Base64 is omitted unless explicitly requested."""

    type: Literal["text", "image", "audio", "video"]
    text: str | None = None
    annotations: list[dict[str, Any]] = Field(default_factory=list)
    mime_type: str | None = None
    path: str | None = None
    uri: str | None = None
    file_name: str | None = None
    data: str | None = None
    sample_rate: int | None = None
    channels: int | None = None


class MediaResult(BaseModel):
    id: str
    status: str
    model: str | None = None
    text: str
    outputs: list[OutputContent] = Field(default_factory=list)
    usage: dict[str, Any] | None = None


def decode_media(data: str, *, limit: int | None = None) -> bytes:
    if limit is not None and len(data) > MAX_BASE64_LENGTH:
        raise ToolError("Inline media exceeds 10 MiB. Use upload_file and uri instead.")
    try:
        decoded = base64.b64decode(data, validate=True)
    except ValueError, binascii.Error:
        raise ToolError(
            "Media data must be valid base64, without a data URI prefix."
        ) from None
    if not decoded:
        raise ToolError("Media data must not be empty.")
    if limit is not None and len(decoded) > limit:
        raise ToolError("Inline media exceeds 10 MiB. Use upload_file and uri instead.")
    return decoded


def local_file(path: str) -> Path:
    file = Path(path)
    if not file.is_absolute():
        raise ToolError("path must be absolute.")
    try:
        if not file.is_file():
            raise ToolError("path must point to a readable regular file.")
    except OSError:
        raise ToolError("Could not inspect the local media file.") from None
    return file


def _read_inline(path: str) -> bytes:
    try:
        with local_file(path).open("rb") as file:
            data = file.read(MAX_INLINE_BYTES + 1)
    except OSError:
        raise ToolError("Could not read the local media file.") from None
    if len(data) > MAX_INLINE_BYTES:
        raise ToolError("Inline media exceeds 10 MiB. Use upload_file and uri instead.")
    if not data:
        raise ToolError("The local media file is empty.")
    return data


async def media_contents(
    media: list[MediaInput] | None, *, allowed: set[str]
) -> list[dict[str, Any]]:
    contents = []
    total_bytes = 0
    for item in media or []:
        if item.type not in allowed:
            raise ToolError(
                f"This tool accepts only {', '.join(sorted(allowed))} media."
            )
        block: dict[str, Any] = {"type": item.type, "mime_type": item.mime_type}
        if item.path is not None:
            data = await asyncio.to_thread(_read_inline, item.path)
            total_bytes += len(data)
            block["data"] = base64.b64encode(data).decode("ascii")
        elif item.data is not None:
            total_bytes += len(decode_media(item.data, limit=MAX_INLINE_BYTES))
            block["data"] = item.data
        else:
            block["uri"] = item.uri
        if total_bytes > MAX_INLINE_BYTES:
            raise ToolError(
                "Total inline media exceeds 10 MiB. Use upload_file and uri."
            )
        contents.append(block)
    return contents


def output_directory(directory: str | None) -> Path:
    if directory is not None and not directory.strip():
        raise ToolError("output_directory must not be blank.")
    configured = (
        directory
        if directory is not None
        else os.getenv("GEMINI_OUTPUT_DIR", "").strip()
    )
    path = Path(configured) if configured else Path.cwd() / "generated-media"
    if not path.is_absolute():
        raise ToolError("output_directory / GEMINI_OUTPUT_DIR must be absolute.")
    if path.exists() and not path.is_dir():
        raise ToolError("output_directory must be a directory.")
    return path


_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "audio/wav": ".wav",
    "audio/mp3": ".mp3",
    "audio/mpeg": ".mp3",
    "audio/l16": ".pcm",
    "audio/mulaw": ".mulaw",
    "audio/alaw": ".alaw",
    "audio/ogg": ".ogg",
    "audio/ogg_opus": ".ogg",
    "audio/flac": ".flac",
}


@contextmanager
def media_output_file(
    directory: Path, kind: str, mime_type: str | None
) -> Iterator[tuple[IO[bytes], str]]:
    """Create a private unique file, removing it if writing fails."""
    try:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, path = tempfile.mkstemp(
            prefix=f"{kind}-",
            suffix=_EXTENSIONS.get((mime_type or "").split(";")[0].lower(), ".bin"),
            dir=directory,
        )
        try:
            with os.fdopen(fd, "wb") as file:
                yield file, path
        except BaseException:
            Path(path).unlink(missing_ok=True)
            raise
    except OSError:
        raise ToolError(
            "Could not save generated media. Check output directory permissions. "
            "Retrieve the interaction by its ID to retry if an ID was returned."
        ) from None


def _save_media(directory: Path, block: dict[str, Any]) -> str:
    data = decode_media(block["data"])
    with media_output_file(directory, block["type"], block.get("mime_type")) as (
        file,
        path,
    ):
        file.write(data)
    return path


def google_file_name(uri: str) -> str | None:
    """Extract Google resource names without accepting arbitrary download hosts."""
    parsed = urlsplit(uri)
    if parsed.scheme and (
        parsed.scheme != "https" or parsed.netloc != "generativelanguage.googleapis.com"
    ):
        return None
    match = re.fullmatch(
        r"(?:/v1(?:beta)?/)?(files/[a-z0-9][a-z0-9-]{0,39})(?::download)?",
        parsed.path,
    )
    return match[1] if match else None


async def media_result(
    response: interactions.Interaction,
    directory: Path,
    *,
    include_inline_data: bool = False,
) -> MediaResult:
    outputs = []
    text = []
    # Convenience properties return only the last output. Iterate all model
    # outputs to retain interleaved lyrics, multiple images, and word annotations.
    for step in response.steps or []:
        if step.type != "model_output":
            continue
        for content in step.content or []:
            block = content.model_dump(mode="json", by_alias=True, exclude_none=True)
            if block["type"] == "text":
                text.append(block["text"])
            elif block["type"] in {"image", "audio", "video"}:
                if block.get("uri"):
                    block["file_name"] = google_file_name(block["uri"])
                if block.get("data"):
                    try:
                        block["path"] = await asyncio.to_thread(
                            _save_media, directory, block
                        )
                    except ToolError as exc:
                        raise ToolError(
                            f"{exc} Interaction ID: {response.id or 'unavailable'}."
                        ) from None
                if not include_inline_data:
                    block.pop("data", None)
            else:
                continue
            outputs.append(OutputContent.model_validate(block))
    return MediaResult(
        id=response.id or "",
        status=response.status,
        model=response.model,
        text="\n".join(text),
        outputs=outputs,
        usage=response.usage.model_dump(mode="json", exclude_none=True)
        if response.usage
        else None,
    )
