# MCP tools reference

This page documents every tool exposed by the Gemini MCP server. Tool arguments
are JSON objects supplied by an MCP client. Tools that call Google require
`GEMINI_API_KEY` or `GOOGLE_API_KEY`; `GEMINI_API_KEY` takes precedence. Google
generation and file operations may incur charges. The guide tool is local and
does not require a key.

The server uses Google's Interactions API for generation. It does
not silently switch to a different API or legacy model. The media model catalog
is a dated snapshot. Media tool schemas show supported model IDs, but this
server does not expose account-specific model availability.

## Shared media conventions

### Supplying input media

Media inputs have `type`, `mime_type`, and exactly one source:

| Field | Meaning |
| --- | --- |
| `path` | Absolute path to a regular file on the machine running this server |
| `data` | Base64-encoded bytes, without a `data:` prefix |
| `uri` | A Google Files URI or another URI the selected model supports; the server passes it to Google and does not fetch it |

Supported `type` values are `image`, `audio`, `video`, and `document` (for
PDFs). The MIME type must match the type, for example `image/png`,
`audio/mp3`, `video/mp4`, or `application/pdf`. The server limits the combined
local-file and base64 media in one request to 10 MiB. Use `upload_file` for
larger files, then pass the returned `uri` and `mime_type` to a media tool.

### Media results and generated files

Media generation returns a `MediaResult`:

| Field | Meaning |
| --- | --- |
| `id` | Google interaction ID, used to poll, cancel, delete, or continue stored work |
| `status` | Google interaction status; an empty output does not imply success |
| `model` | Model reported for the interaction, if available |
| `text` | Joined text from model output blocks |
| `outputs` | All model output blocks in their original order, including text annotations and media |
| `usage` | Token/usage metadata when Google returns it |

Inline image, audio, and video outputs are saved to unique local files. The
returned output block includes an absolute `path`; base64 `data` is omitted by
default. Set `include_inline_data: true` on tools that expose it to also return
base64. By default, files are written under `generated-media/` in the server's
working directory. `GEMINI_OUTPUT_DIR` or a tool's `output_directory` can select
another absolute directory. Output files are private and are not automatically
removed.

Some video outputs use a Google URI instead of inline bytes. Those URIs are not
downloaded automatically. A recognized Google Files URI includes `file_name`;
poll it with `get_file` until `ACTIVE`, then use `download_file`.

### Stored and background interactions

The server always asks Google to store created interactions, including
media generation and transcription. No tool exposes a storage toggle.
Use the returned `id` with `get_interaction` to poll background work. Pass an
interaction ID as `previous_interaction_id` to continue where supported.
Options such as output format, voice, and search grounding apply to that call
and should be repeated on later turns when needed. The server does not
automatically retry generation requests.

Timeouts default to 60 seconds for interaction metadata
requests, and 600 seconds for media creation and file transfers. Tools exposing
`timeout_seconds` accept values from 1 through 1800.

## Image generation

### `generate_image`

Generates an image from a prompt, edits supplied reference media, or continues a
stored interaction. It uses the current Nano Banana image models.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `prompt` | Yes | — | Nonblank image-generation or editing instructions |
| `media` | No | — | Up to 20 inputs of type `image`, `video`, or `document`; no more than 14 may be images |
| `model` | No | `gemini-3.1-flash-image` | `gemini-3.1-flash-image`, `gemini-3.1-flash-lite-image`, or `gemini-3-pro-image` |
| `aspect_ratio` | No | Model default | One of `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`, `1:8`, `8:1`, `1:4`, or `4:1` |
| `image_size` | No | `1K` | `512`, `1K`, `2K`, or `4K` |
| `include_text` | No | `true` | Request text alongside generated image output |
| `google_search` | No | `false` | Enable Google Search grounding |
| `previous_interaction_id` | No | — | Stored interaction to continue or edit |
| `background` | No | `false` | Run as background work; the interaction is retained automatically for polling |
| `timeout_seconds` | No | `600` | Request timeout, 1–1800 seconds |
| `output_directory` | No | `GEMINI_OUTPUT_DIR` or `generated-media/` | Absolute directory for saved inline results |
| `include_inline_data` | No | `false` | Include output base64 data as well as saving it locally |

Lite supports only `1K` and does not support Google Search. Pro does not support
`512`. The tool may return multiple images and text blocks.

## Video generation

### `generate_omni`

Uses Google's current Omni model, `gemini-omni-1.1-flash`, through Interactions
to generate video with native audio, edit or extend video, and use image
references for interpolation or reference-guided generation.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `prompt` | Yes | — | Nonblank scene, audio, transition, editing, or extension instructions |
| `media` | No | — | Up to 20 inputs of type `image`, `audio`, or `video`; order matters for reference frames |
| `model` | No | `gemini-omni-1.1-flash` | The current Omni model |
| `aspect_ratio` | No | Model default | `16:9` or `9:16` |
| `resolution` | No | `720p` | `360p`, `720p`, `1080p`, or `4k` |
| `duration_seconds` | No | Model default | Requested duration, 3–10 seconds |
| `task` | No | — | `text_to_video`, `image_to_video`, `reference_to_video`, `edit`, or `extend` |
| `delivery` | No | `uri` | `uri` for Google Files output or `inline` for returned bytes |
| `previous_interaction_id` | No | — | Stored interaction to continue, edit, or extend |
| `background` | No | `false` | Run as background work; the interaction is retained automatically for polling |
| `timeout_seconds` | No | `600` | Request timeout, 1–1800 seconds |
| `output_directory` | No | `GEMINI_OUTPUT_DIR` or `generated-media/` | Absolute directory for saved inline results |
| `include_inline_data` | No | `false` | Include output base64 data as well as saving it locally |

`edit` and `extend` require a video input or `previous_interaction_id`.
`image_to_video` and `reference_to_video` require at least one image. Prompt-based
editing is preferred when no explicit task is needed. URI delivery avoids large
responses; it does not save or download the URI content.

## Audio transcription and speech generation

### `transcribe_audio`

Transcribes one audio input with Google's dedicated Transcribe model. This is
configuration-based ASR and has no free-form prompt argument.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `audio` | Yes | — | One `audio` media input |
| `model` | No | `gemini-3.5-transcribe` | Current transcription model |
| `mode` | No | `verbatim` | `verbatim` or cleaned-up `smart` transcription |
| `language_codes` | No | Automatic detection | Language hints, for example `["en-US"]` |
| `custom_vocabulary` | No | — | Up to 1,000 domain-specific terms |
| `diarization` | No | `false` | Attribute speech to speakers in verbatim mode |
| `word_timestamps` | No | `false` | Request word-level timestamp annotations in verbatim mode |
| `background` | No | `false` | Run as background work; the interaction is retained automatically for polling |
| `timeout_seconds` | No | `600` | Request timeout, 1–1800 seconds |

Smart mode cannot be combined with diarization or word timestamps. Custom
vocabulary cannot be combined with either of those options. The result includes
transcription text and any ordered annotation blocks, such as `word_info`.

### `generate_speech`

Generates spoken audio from either a single transcript or structured dialogue.
Provide exactly one of `text` or `turns`.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `text` | One of `text` or `turns` | — | Verbatim text to speak |
| `turns` | One of `text` or `turns` | — | Nonempty list of dialogue turns; each has `text` and optional `speaker` and `style` |
| `voice` | No | `Kore` | Existing voice ID for single-speaker speech |
| `style` | No | — | Delivery direction; it is not spoken transcript text |
| `language` | No | Model default | Language for single-speaker speech; set per speaker for dialogue |
| `speakers` | No | — | Exactly two distinct speaker definitions when using named dialogue turns |
| `model` | No | `gemini-3.8-flash-tts` | `gemini-3.8-flash-tts` or `gemini-3.8-flash-lite-tts` |
| `mime_type` | No | `audio/wav` | `audio/wav`, `audio/l16`, `audio/mulaw`, or `audio/alaw` |
| `sample_rate` | No | Model default | Requested sample rate in Hz; must be positive |
| `previous_interaction_id` | No | — | Stored interaction to continue |
| `background` | No | `false` | Run as background work; the interaction is retained automatically for polling |
| `timeout_seconds` | No | `600` | Request timeout, 1–1800 seconds |
| `output_directory` | No | `GEMINI_OUTPUT_DIR` or `generated-media/` | Absolute directory for saved inline results |
| `include_inline_data` | No | `false` | Include output base64 data as well as saving it locally |

Each speaker definition has `speaker` (distinct name), `voice`, and optional
`language`. Each dialogue turn that names a speaker must match one of the
configured speakers. With `speakers`, do not set top-level `language`. Existing
voice IDs can be used; this tool does not create or clone voices. WAV data is
saved as returned, without adding another header.

## Music generation

### `generate_music`

Generates batch music with Lyria from a text prompt and optional image
references. Song length, BPM, structure, lyrics, and instrumental direction are
prompt instructions, not separate tool arguments.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `prompt` | Yes | — | Nonblank musical direction, optionally including lyrics |
| `media` | No | — | Up to 10 image inputs for visual inspiration |
| `model` | No | `lyria-3.5` | `lyria-3.5` for songs or `lyria-3-clip-preview` for short clips |
| `mime_type` | No | `audio/mp3` | `audio/mp3` or `audio/wav` |
| `include_text` | No | `true` | Request lyrics/text alongside audio |
| `background` | No | `false` | Run as background work; the interaction is retained automatically for polling |
| `timeout_seconds` | No | `600` | Request timeout, 1–1800 seconds |
| `output_directory` | No | `GEMINI_OUTPUT_DIR` or `generated-media/` | Absolute directory for saved inline results |
| `include_inline_data` | No | `false` | Include output base64 data as well as saving it locally |

The clip model supports MP3 only; WAV requires `lyria-3.5`. This is batch
generation, not the separate Lyria RealTime API.

## Interaction lifecycle

### `get_interaction`

Retrieves or polls an explicitly identified stored interaction.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `interaction_id` | Yes | — | Google interaction ID |
| `output_directory` | No | `GEMINI_OUTPUT_DIR` or `generated-media/` | Absolute directory for any inline media outputs |
| `include_inline_data` | No | `false` | Include output base64 data as well as saving it locally |

Returns a `MediaResult` containing model outputs, not stored input or reasoning
steps. Retrieving inline outputs again creates new unique local files.

### `cancel_interaction`

Requests cancellation of a running background interaction.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `interaction_id` | Yes | — | Google interaction ID |

Returns the interaction's `MediaResult`. Cancellation may not undo charges
already incurred.

### `delete_interaction`

Deletes one explicitly named stored Google interaction. This does not delete
local output files.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `interaction_id` | Yes | — | Google interaction ID |

**Returns:** `{"id": "...", "status": "deleted"}`.

## Google Files

### `upload_file`

Uploads an absolute local file to Google's Files API for use as media input.
Uploading sends the file to Google. Files can remain in `PROCESSING`; poll
`get_file` until the state is `ACTIVE` before using the returned URI. Uploaded
files expire after 48 hours.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `path` | Yes | — | Absolute path to a local regular file |
| `mime_type` | Yes | — | File MIME type |
| `display_name` | No | Google default | Nonblank display name |
| `timeout_seconds` | No | `600` | Upload timeout, 1–1800 seconds |

**Returns:** file `name`, `uri`, `mime_type`, `state`, optional `display_name`,
`size_bytes`, and `expiration_time`.

### `get_file`

Checks one Google Files resource's processing state and metadata.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `name` | Yes | — | Google resource name in the form `files/FILE_ID` |

**Returns:** the same file metadata as `upload_file`. Use the URI only when the
state is `ACTIVE`; do not use `PROCESSING` or `FAILED` files as ready inputs.

### `list_files`

Lists uploaded Google Files resources and their processing states.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `limit` | No | `100` | Maximum number of files to return, 1–1,000 |

**Returns:** an array of file metadata objects. Results may be fewer than the
limit if fewer files are available.

### `delete_file`

Deletes one explicitly named Google Files resource. It does not delete any local
files. Deleting a file may prevent pending interactions from using it.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `name` | Yes | — | Google resource name in the form `files/FILE_ID` |

**Returns:** `{"name": "...", "status": "deleted"}`.

### `download_file`

Streams an `ACTIVE` generated Google file to a unique local file. Use the
`file_name` from a generated media output URI. This tool accepts Google Files
resource names only; it does not fetch arbitrary URLs and does not download
uploaded input files.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `name` | Yes | — | Google resource name in the form `files/FILE_ID` |
| `output_directory` | No | `GEMINI_OUTPUT_DIR` or `generated-media/` | Absolute directory for the downloaded file |
| `timeout_seconds` | No | `600` | Download timeout, 1–1,800 seconds |

**Returns:** `name`, absolute local `path`, and `mime_type`.

## Official prompting guide

`get_prompt_guide` returns bundled, near-verbatim excerpts of official Google
documentation with source links, attribution, disclosed modifications, supported
model IDs, and separate MCP usage notes. It is offline, read-only, and free to
call; it does not require an API key or make generation requests. Its content is
a dated snapshot, not a live documentation lookup. The server instructions ask
clients to read the matching guide in full before the first media call in a
session.

Guide results include `title`, `related_tools`, `models`, `retrieved_on`,
`sources` (title, URL, selected sections, modifications, and Markdown),
`attribution`, `license`, `license_url`, and `mcp_notes`.

`get_prompt_guide` selects the offline guide by task.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `guide` | Yes | — | `image`, `video`, `speech`, `music`, or `transcription` |

The guide covers Nano Banana image generation/editing, Omni video generation and
editing, Gemini TTS, Lyria music, or audio transcription, depending on `guide`. Results include `related_tools`, supported `models`,
`retrieved_on`, attributed source excerpts and links, modification notes,
license details, and separate MCP usage notes.

For source pages, snapshot boundaries, and refresh steps, see
[`prompt-guides.md`](prompt-guides.md). Model defaults and API boundaries are
also described in [`media-api.md`](media-api.md).
