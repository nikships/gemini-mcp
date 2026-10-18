<div align="center">

<img src="https://raw.githubusercontent.com/nikships/gemini-mcp/main/docs/assets/hero.jpg" alt="A coding agent connected through the Gemini sparkle to hearing, voice, images, music, and video" width="100%">

# aio-gemini-mcp

Give your AI agent ears, a voice, eyes, and a studio. One MCP server for Gemini's image, video, speech, transcription, and music models.

[![Google Gemini](https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)](https://ai.google.dev/gemini-api/docs)
[![PyPI](https://img.shields.io/pypi/v/aio-gemini-mcp?style=for-the-badge)](https://pypi.org/project/aio-gemini-mcp/)
[![Downloads](https://img.shields.io/pypi/dm/aio-gemini-mcp?style=for-the-badge)](https://pypi.org/project/aio-gemini-mcp/)
[![Build](https://img.shields.io/github/actions/workflow/status/nikships/gemini-mcp/publish.yml?style=for-the-badge)](https://github.com/nikships/gemini-mcp/actions)

</div>

## What is this?

Most coding agents only read and write text. This server plugs them into Google's
Gemini media models so they can also **hear** audio, **speak**, **see and make
images**, **compose music**, and **produce video**, all as ordinary MCP tool calls.

| Give your agent... | With | Example |
| --- | --- | --- |
| Ears | `transcribe_audio` | Turn a meeting recording into a diarized transcript with word timestamps |
| A voice | `generate_speech` | Read a changelog aloud, or script a two-speaker dialogue |
| Eyes and a canvas | `generate_image` | Create or edit images, grounded in Google Search and Image Search |
| A composer | `generate_music` | Write an instrumental, a song with lyrics, or music inspired by an image |
| A camera | `generate_omni` | Generate, edit, and extend video, including first/last-frame interpolation |

It is a stdio [FastMCP](https://gofastmcp.com) server built on the Google Gen AI
SDK and the Interactions API. It starts no HTTP server and opens no port.
Stdout carries MCP messages only, and diagnostics go to stderr.

## Quick Start

You need [`uv`](https://docs.astral.sh/uv/) and a
[Gemini API key](https://aistudio.google.com/apikey). Add the server to your MCP
client's `mcpServers` configuration (also in
[`mcp-config.example.json`](mcp-config.example.json)). `uvx` fetches the latest
release from [PyPI](https://pypi.org/project/aio-gemini-mcp/):

```json
{
  "mcpServers": {
    "gemini": {
      "command": "uvx",
      "args": ["aio-gemini-mcp@latest"],
      "env": {
        "GEMINI_API_KEY": "YOUR_GEMINI_API_KEY"
      }
    }
  }
}
```

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Gemini Developer API key. Takes precedence over `GOOGLE_API_KEY`. |
| `GOOGLE_API_KEY` | Fallback key. |
| `GEMINI_OUTPUT_DIR` | Absolute directory for saved media. Defaults to `generated-media/` in the server's working directory. |

`.env` files are not loaded. A missing key does not stop startup or tool
discovery, only the tools that call Google. Prompts are sent to Google, and API
use may incur charges.

## Tools

| Tool | Purpose |
| --- | --- |
| `generate_image` | Nano Banana image generation and editing, with optional Google Search and Image Search grounding |
| `generate_omni` | Omni video generation, editing, extension, and first/last-frame interpolation |
| `transcribe_audio` | Speech recognition with smart/verbatim modes, diarization, and word timestamps |
| `generate_speech` | Single- or two-speaker TTS with voice, language, and delivery style controls |
| `generate_music` | Lyria songs, instrumental music, short clips, lyrics, and image-inspired music |
| `get_prompt_guide` | Google's official prompting guide for `image`, `video`, `speech`, `music`, or `transcription` |
| `get_interaction` / `cancel_interaction` / `delete_interaction` | Poll, cancel, or delete stored Google interactions |
| `upload_file` / `get_file` / `list_files` / `delete_file` / `download_file` | Manage Google Files for large inputs and generated outputs |

See [`docs/tools.md`](docs/tools.md) for every argument, default, constraint, and return shape.

## Examples

Tool arguments are JSON for your MCP client, not terminal commands.

**Generate an image**

```json
{
  "prompt": "Create a cinematic watercolor landscape",
  "aspect_ratio": "16:9",
  "image_size": "2K"
}
```

Set `"image_search": true` when the image must depict a real subject accurately, such as a species or landmark. To edit a local image, add `"media": [{"type": "image", "mime_type": "image/png", "path": "/ABSOLUTE/image.png"}]`.

**Transcribe audio**

```json
{
  "audio": {"type": "audio", "mime_type": "audio/mp3", "path": "/ABSOLUTE/audio.mp3"},
  "language_codes": ["en-US"],
  "diarization": true,
  "word_timestamps": true
}
```

**Speak with two voices**

```json
{
  "turns": [
    {"text": "Hello!", "speaker": "Joe", "style": "cheerful"},
    {"text": "Hi Joe.", "speaker": "Jane", "style": "relaxed"}
  ],
  "speakers": [
    {"speaker": "Joe", "voice": "Puck"},
    {"speaker": "Jane", "voice": "Kore"}
  ]
}
```

**Compose music**

```json
{
  "prompt": "A two-minute instrumental jazz track in D minor, with piano, upright bass, and brushed drums",
  "mime_type": "audio/mp3"
}
```

**Generate video in the background**

```json
{
  "prompt": "A slow tracking shot of waves at sunset, with ocean sounds",
  "aspect_ratio": "16:9",
  "resolution": "1080p",
  "duration_seconds": 8,
  "background": true
}
```

Use the returned `id` with `get_interaction` until the status is terminal. The server never auto-polls or auto-retries, so a retry cannot create a duplicate charge.

## How it behaves

- **Inputs.** Each `media` item takes exactly one of an absolute `path`, base64 `data`, or a Google Files `uri`. Local and base64 input is capped at 10 MiB per request. For larger files, use `upload_file`, then `get_file` until the state is `ACTIVE`.
- **Outputs.** Binary results are saved with unique, private (`0600`) file names and never overwrite existing files. The result lists the absolute `path`. Base64 is omitted unless you set `include_inline_data: true`.
- **Continuation.** Every call is stored with Google. Pass a returned `id` as `previous_interaction_id` to continue or edit. Options such as voices and output format apply per call and must be repeated.
- **Honest status.** `completed`, `blocked`, `incomplete`, `failed`, and `cancelled` are returned as Google reports them, even when the output is empty.
- **Timeouts.** Metadata requests time out after 60 seconds. Media creation, upload, and download default to 600 seconds and accept `timeout_seconds` from 1 to 1800.
- **Errors.** Upstream error details are redacted from tool errors.

## Prompting guides

`get_prompt_guide` is read-only, offline, and free. It needs no API key and sends
nothing to Google. It returns Google's own wording, templates, and examples (not
AI-written summaries) with sources, the retrieval date, and notes on how the advice
maps to these tools. Call it before building a media request.

```json
{"guide": "music"}
```

The guides are a bundled snapshot dated **2026-10-18**, not a live lookup. See
[`docs/prompt-guides.md`](docs/prompt-guides.md) for sources, attribution, and
refresh steps.

## Models

Model IDs were verified on **2026-10-18** against Google's
[model catalog](https://ai.google.dev/gemini-api/docs/models). Tool schemas list
the supported choices but cannot report what your account can access. There is no
legacy fallback.

| Capability | Default | Other choices |
| --- | --- | --- |
| Images | `gemini-nano-banana-2.1` | `gemini-3.1-flash-image`, `gemini-3.1-flash-lite-image`, `gemini-3-pro-image` |
| Video | `gemini-omni-1.1-flash` | None |
| Transcription | `gemini-3.5-transcribe` | None |
| Speech | `gemini-3.8-flash-tts` | `gemini-3.8-flash-lite-tts` |
| Music | `lyria-3.5` | `lyria-3-clip-preview` |

Every generation call uses `client.aio.interactions.create`. Live audio,
Lyria RealTime, and voice design or cloning use separate APIs and are out of scope.
See [`docs/media-api.md`](docs/media-api.md) for sources and per-model constraints.

## Project Structure

```
docs/
  media-api.md
  prompt-guides.md
  tools.md
src/
  aio_gemini/
    data/guides/
    __init__.py
    __main__.py
    catalog.py
    guides.py
    media.py
    server.py
tests/
mcp-config.example.json
pyproject.toml
uv.lock
```

## Documentation

| Resource | Description |
| --- | --- |
| [`docs/tools.md`](docs/tools.md) | Arguments, defaults, accepted values, and return shapes for every tool |
| [`docs/media-api.md`](docs/media-api.md) | Model catalog sources and API boundaries |
| [`docs/prompt-guides.md`](docs/prompt-guides.md) | Guide sources, attribution, and how to refresh them |

## Development

```sh
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv build
```

Tests mock Google requests, check the real SDK's Interactions HTTP transport, and
run real stdio subprocesses against current and legacy MCP clients. They need no
credentials and make no Google API calls. Live generation needs your own API key
and is not covered.

To run a local checkout instead of the published package:

```sh
uv --directory /path/to/gemini-mcp run --frozen aio-gemini-mcp
```

The server waits for MCP messages on stdin, so launch it from an MCP client
rather than a terminal.

---

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=nikships/gemini-mcp&type=Date)](https://star-history.com/#nikships/gemini-mcp&Date)

</div>
