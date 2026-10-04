# Gemini MCP server

A Python FastMCP server using **stdio**, the official **Google Gen AI SDK**, and
the **Google Interactions API** for generation, not `models.generate_content`.
No HTTP server or listening port is started. Stdout is reserved for MCP messages;
diagnostics go to stderr.

## MCP configuration

Add this to your MCP client's `mcpServers` configuration (also available as
[`mcp-config.example.json`](mcp-config.example.json)). It needs only `uv`; `uvx`
fetches and runs the server from [PyPI](https://pypi.org/project/aio-gemini-mcp/):

```json
{
  "mcpServers": {
    "gemini": {
      "command": "uvx",
      "args": [
        "aio-gemini-mcp@latest"
      ],
      "env": {
        "GEMINI_API_KEY": "YOUR_GEMINI_API_KEY"
      }
    }
  }
}
```

Optional `env` entries: `GEMINI_MODEL` (default text model, `gemini-3.8-flash`)
and `GEMINI_OUTPUT_DIR` (absolute path for saved media). Client configuration
formats can vary.

## Setup

This machine already has uv and Python installed. For a fresh checkout:

```sh
cd /home/factory-user/gemini-mcp
uv sync --frozen
```

uv installs the Python version in `.python-version` if needed. `uv.lock` pins all
dependencies for reproducible installs. Stable versions selected at setup:

| Component | Version |
| --- | --- |
| uv | 0.12.22 |
| Python | 3.14.8 |
| FastMCP | 4.0.10 |
| google-genai | 2.28.0 |

uv is installed in `/home/factory-user/.local/bin`. Open a new terminal to pick up
the updated PATH, or use that absolute path.

## Run

Supply your Gemini Developer API key through the MCP client's environment.
`GEMINI_API_KEY` takes precedence over `GOOGLE_API_KEY`. No key is stored in this
project. `.env` files are **not** automatically loaded.

```sh
uv --directory /home/factory-user/gemini-mcp run --frozen aio-gemini-mcp
```

Also supported: `uv run python -m aio_gemini` from the project directory.
The server waits for MCP messages on stdin; it is not an interactive terminal app.
An MCP client should launch it as a subprocess, as in the
[MCP configuration](#mcp-configuration) above.

## Tools

| Tool | Purpose |
| --- | --- |
| `generate_text` | Create a Gemini interaction and return its ID, status, and text |
| `generate_image` | Nano Banana image generation and editing, with optional Google Search |
| `generate_omni` | Omni video generation, editing, extension, and first/last-frame interpolation |
| `transcribe_audio` | Dedicated speech recognition, smart/verbatim modes, diarization, and word timestamps |
| `generate_speech` | Single- or two-speaker TTS with voice, language, and delivery style controls |
| `generate_music` | Lyria songs, instrumental music, clips, lyrics, and image-inspired music |
| `analyze_media` | Understand images, audio, video (static/agentic), and PDFs |
| `get_interaction` | Retrieve or poll stored interactions and save inline media |
| `cancel_interaction` / `delete_interaction` | Explicitly cancel background work or delete stored Google interactions |
| `upload_file` / `get_file` / `list_files` / `delete_file` | Manage reusable Google Files inputs and processing readiness |
| `download_file` | Stream an ACTIVE generated Google file to a unique local file |
| `get_prompt_guide` | Official prompting guide by `guide`: `image`, `video`, `speech`, `music`, `transcription`, or `analysis` |

See [`docs/tools.md`](docs/tools.md) for arguments, defaults, accepted values,
constraints, and return shapes for every tool.

`generate_text` calls `client.aio.interactions.create`. It accepts `prompt`,
optional `model`, optional `system_instruction`, `max_output_tokens` (default
4096, allowed range 1–65536), and optional `previous_interaction_id`. Model-specific
limits still apply. Set `GEMINI_MODEL` to change the default, `gemini-3.8-flash`,
or pass `model` per request. Media tool schemas expose their supported model
choices, but do not report account-specific access.

Generation now returns a structured object, not the old bare text string:

```json
{"id": "interaction-id", "status": "completed", "text": "Hello!"}
```

All Interactions calls are stored with Google automatically. To continue a
conversation, pass the returned `id` as `previous_interaction_id` on the next
call. The server does not expose a storage toggle; this does not bypass Google's
other data policies. System instructions and generation options are supplied on
each call.

`generate_text` remains non-streaming and foreground-only. The returned status
is preserved even if text is empty, rather than reporting an incomplete or
blocked response as successful text.

Text and interaction metadata requests use a 60-second timeout. Media creation,
upload, and download default to 600 seconds, configurable with `timeout_seconds`
(1–1800). Google requests use asynchronous I/O. Clients
are closed after each tool call. Upstream error details are redacted from tool
errors. Prompts are sent to Google and API use may incur charges. Missing keys
do not prevent startup or tool discovery.

## Official prompting guides

`get_prompt_guide` is **read-only, offline, and free to call**. It needs no API
key, generates nothing, and sends nothing to Google. Call it before constructing
a media request. It takes a required `guide`:

```json
{"guide": "music"}
```

`guide` is one of `image`, `video`, `speech`, `music`, `transcription`, or
`analysis`. For `analysis`, an optional `media_type` narrows the guide:

```json
{"guide": "analysis", "media_type": "document"}
```

Use `image`, `audio`, `video`, or `document` (PDF), or omit `media_type` for `all`.
The analysis guide always includes general file-prompting strategies.
`media_type` is ignored for other guides.

The full guide text is returned in the response, not just a link. Guides return
closely preserved **official wording, templates, and examples**, not AI-written
summaries. `sources` includes each page's `title`, `url`,
selected `sections`, `markdown`, and disclosed `modifications`. Results also
include `retrieved_on`, related tools, supported models, Google attribution,
the CC BY 4.0 license link, and separate `mcp_notes` explaining how the guidance
maps to this server.

This is a bundled **2026-10-03 documentation snapshot**, not a live lookup.
Unrelated API code and illustrative media are omitted. The music guide preserves
the batch-generation sections of Google's
[Lyria prompt guide](https://ai.google.dev/gemini-api/docs/lyria-prompt-guide),
not its separate RealTime API examples. Transcription uses configuration rather
than a free-form prompt, so its guide preserves official configuration guidance
instead of inventing prompting instructions. Separate voice APIs mentioned in
the TTS guide are not implemented by this MCP.

See [`docs/prompt-guides.md`](docs/prompt-guides.md) for sources, attribution,
snapshot boundaries, and refresh instructions.

## Media models and API boundaries

Model IDs and request formats were verified on **2026-10-03** using the
`retrieving-developer-knowledge` skill and Google Developer Knowledge MCP.
The [official model catalog](https://ai.google.dev/gemini-api/docs/models) and
task-specific guides are the source of truth, not remembered model names.

| Capability | Default | Other current choices |
| --- | --- | --- |
| Text and media analysis | `gemini-3.8-flash` | Text retains its explicit model/environment override |
| Images | `gemini-3.1-flash-image` | `gemini-3.1-flash-lite-image`, `gemini-3-pro-image` |
| Video / Omni | `gemini-omni-1.1-flash` | None |
| Transcription | `gemini-3.5-transcribe` | None |
| TTS | `gemini-3.8-flash-tts` | `gemini-3.8-flash-lite-tts` |
| Music | `lyria-3.5` | `lyria-3-clip-preview`, the current short-clip specialist |

Media tool model choices are constrained to these current families, with **no
legacy fallback**. `GEMINI_MODEL` affects only `generate_text`, not media tools.
This is a dated snapshot, not automatic model discovery or a promise of account
access. Model schemas expose the supported choices, not account availability.
Refresh the catalog from official docs before adding future models.

All generation and analysis calls use `client.aio.interactions.create`.
There is no `generateContent`, Imagen, or fallback to another video-generation
API. **Live audio/live transcription**, **Lyria RealTime**, and **voice
design/replication** use separate APIs and are intentionally outside this
Interactions-only suite. TTS accepts existing custom voice IDs but does not
create or clone voices.

Sources and model-specific constraints are recorded in
[`docs/media-api.md`](docs/media-api.md).

## Media inputs, outputs, and examples

Tool arguments below are JSON for your MCP client, not terminal commands.
`media` items require `type` (`image`, `audio`, `video`, or `document`),
`mime_type`, and **exactly one** of:

- `path`: an absolute regular file path on the machine running this server.
- `data`: plain base64, without a `data:` prefix.
- `uri`: a Google Files URI or another URI supported by the selected model.
  URI inputs are passed to Google, never fetched by this server.

Local/base64 inputs have a **10 MiB total server memory limit** per request,
independent of Google's larger file/model limits. For larger input, call
`upload_file` with an absolute `path` and `mime_type`. Poll `get_file` using its
`name` until `state` is `ACTIVE`, then use the returned `uri` and `mime_type`.
`PROCESSING` is not ready and `FAILED` should not be retried as ready.
Uploaded files expire after 48 hours. Uploading sends the file to Google.
Deleting an uploaded file can prevent pending interactions from using it.

Media results include `id`, `status`, `model`, `text`, ordered `outputs`, and
`usage` when available. All model output blocks are retained, including
interleaved lyrics, multiple images, and transcription `word_info` annotations.
Stored inputs and thought steps are not returned.

Inline binary outputs are decoded and saved in `GEMINI_OUTPUT_DIR`, defaulting
to `generated-media/` under the server's working directory. Set an absolute
`output_directory` per call to override it. File names are unique and private
(mode `0600`), existing files are never overwritten, and the returned `path` is
absolute. Actual MIME types determine extensions; WAV data is saved as returned,
without adding a second WAV header. Unknown formats use `.bin`. Local outputs
remain until you remove them.

Base64 is omitted from MCP results by default to avoid filling model context.
Set `include_inline_data: true` if you also need it. Local output paths refer to
the server machine, not necessarily the MCP client's machine.

Omni delivery defaults to `"uri"`, which suits large videos. All Interactions
calls are stored automatically. URI outputs have `uri` and, for recognized
Google Files URIs, `file_name`. Poll `get_file` until ACTIVE, then call
`download_file` with that `file_name` to stream it to disk. Downloads accept
Google resource names only, not arbitrary URLs. You can also pass
`delivery: "inline"` to save bytes immediately. Google's current Omni docs note
that `get_interaction` can return inline data even when creation used URI delivery.

### Image generation or editing

Call `generate_image`:

```json
{
  "prompt": "Create a cinematic watercolor landscape",
  "aspect_ratio": "16:9",
  "image_size": "2K"
}
```

To edit a local image, supply
`"media": [{"type": "image", "mime_type": "image/png", "path": "/ABSOLUTE/image.png"}]`.
To edit a stored result, provide its `id` as `previous_interaction_id`.
Use `include_text: false` for image-only output.

### Omni video generation and editing

Call `generate_omni`:

```json
{
  "prompt": "A slow tracking shot of waves at sunset, with ocean sounds",
  "aspect_ratio": "16:9",
  "resolution": "1080p",
  "duration_seconds": 8,
  "background": true
}
```

The tool uses the Omni model and controls. Supply ordered reference images
for first/last frames and describe the transition in the prompt. Image, audio,
and video references can be combined. Prompt for an edit or extension, or use
`task: "edit"` / `"extend"` with an input video or stored `previous_interaction_id`.
Prompt-based control is preferred; explicit tasks impose stricter constraints.
1080p and 4K are upscaled. See the source guide for extension limits and regions.

### Transcription

Call `transcribe_audio`:

```json
{
  "audio": {"type": "audio", "mime_type": "audio/mp3", "path": "/ABSOLUTE/audio.mp3"},
  "language_codes": ["en-US"],
  "diarization": true,
  "word_timestamps": true
}
```

For cleaned-up prose, use `mode: "smart"` without diarization/timestamps.
`custom_vocabulary` cannot be combined with diarization or word timestamps.

### TTS

Call `generate_speech`:

```json
{"text": "Welcome! <short pause> Let's begin.", "voice": "Kore", "style": "warm and friendly"}
```

For two speakers, use structured `turns` instead of `text`:

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

Text is spoken verbatim. Delivery directions belong in `style`, which maps to
`speech_metadata`, not inline prose. Momentary vocal tags can remain in text.
Audio defaults to WAV; `audio/l16`, `audio/mulaw`, and `audio/alaw` are also
supported through `mime_type`. Set `sample_rate` in Hz if needed.

### Lyria music

Call `generate_music`:

```json
{
  "prompt": "A two-minute instrumental jazz track in D minor, with piano, upright bass, and brushed drums",
  "mime_type": "audio/mp3"
}
```

Prompt for song duration, structure, BPM, language, and custom lyrics. Music can
be inspired by up to ten image references. Use `model: "lyria-3-clip-preview"`
for short clips. WAV output requires `lyria-3.5`.

### Background and multi-turn work

Media tools accept `background: true`; interactions are stored automatically.
Use the returned `id` with `get_interaction` until a terminal status is returned.
The server does not auto-poll or auto-retry generation (which could create
duplicate charges). Cancel by ID with `cancel_interaction`. Provide
`previous_interaction_id` to tools that support continuation. Options such as
output format, voices, and search are scoped to each call and must be repeated.
Status is preserved for blocked, incomplete, failed, queued, or cancelled work;
empty output never overrides the upstream status.

## Develop and validate

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv build
```

Tests mock Google requests, verify the real SDK's Interactions HTTP transport,
and exercise real stdio subprocesses with both current and legacy MCP clients.
They need no credentials and make no Google
API calls. Guide tests also check preserved sections/examples, snapshot hashes,
offline operation, read-only annotations, and MCP output schemas. Live generation
requires your own API key and is not covered by these tests.

To upgrade to newer stable dependencies intentionally:

```sh
uv lock --upgrade
uv sync --frozen
uv run pytest
```
