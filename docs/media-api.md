# Media API documentation snapshot

Verified **2026-10-03** with the repository's
`retrieving-developer-knowledge` skill and the Google Developer Knowledge MCP
`search_documents` / `get_documents` tools. Model selection comes from these
retrieved official sources. The installed Google Gen AI SDK is used to verify
request serialization, not to decide which model is current.

## Source of truth

| Source | Decision |
| --- | --- |
| [Models](https://ai.google.dev/gemini-api/docs/models) | Current families: Gemini 3.8 Flash/TTS, Nano Banana 2/Lite/Pro, Omni 1.1 Flash, Transcribe 3.5, Lyria 3.5 and the clip specialist |
| [Interactions overview](https://ai.google.dev/gemini-api/docs/interactions-overview) | Interactions is the recommended unified API; `steps` contains model outputs; storage is optional |
| [Interactions API reference](https://ai.google.dev/api/interactions-api) | Content discriminators, response formats, generation config, and lifecycle endpoints |
| [Image generation](https://ai.google.dev/gemini-api/docs/image-generation) | Image/reference inputs, multi-turn editing, `response_format`, search grounding |
| [Nano Banana 2](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-image) | `gemini-3.1-flash-image`, 512/1K/2K/4K and additional aspect ratios |
| [Nano Banana 2 Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite-image) | `gemini-3.1-flash-lite-image`, 1K only, no search grounding |
| [Omni](https://ai.google.dev/gemini-api/docs/omni) | `gemini-omni-1.1-flash`, multimodal video, edit/extend/interpolate, URI delivery |
| [Omni model](https://ai.google.dev/gemini-api/docs/models/gemini-omni-flash) | Current stable Omni ID, 3–10 second outputs, 360p/720p/1080p/4K |
| [Transcription](https://ai.google.dev/gemini-api/docs/transcribe) | `gemini-3.5-transcribe`, `transcription_config`, `word_info`, compatibility constraints |
| [Speech generation](https://ai.google.dev/gemini-api/docs/speech-generation) | Gemini 3.8 TTS models, `speech_metadata`, single/two-speaker config, WAV/PCM formats |
| [Gemini 3.8 Flash TTS](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash-tts) | Flagship current TTS and migration from legacy TTS; Lite is the current efficiency tier |
| [Music generation](https://ai.google.dev/gemini-api/docs/music-generation) | `lyria-3.5` full songs, `lyria-3-clip-preview` short clips, text/images, MP3/WAV |
| [Background execution](https://ai.google.dev/gemini-api/docs/background-execution) | `background=true`, get/cancel lifecycle, retained state |
| [Files API reference](https://ai.google.dev/api/files) | Resource names, states, expiration, and generated download URIs |

Task-specific guides and the current model catalog can be ahead of enumerated
model lists in the reference or SDK. For example, some retrieved reference
sections still list Lyria 3 Pro and legacy TTS while the music/TTS guides name
their replacements. The server uses current task-specific guides and catalog,
not legacy examples. No automatic fallback is configured.

## Request and output shapes

- Generation uses `client.aio.interactions.create(model=..., input=...)`.
- Media content has `type`, `mime_type`, and either `data` (base64) or `uri`.
  The SDK normalizes a content list into a `user_input` step automatically.
- `response_format` is an object or list with discriminators `text`, `image`,
  `audio`, or `video`. Image size/aspect ratio and audio encoding belong here,
  not in the deprecated `generation_config.image_config`/`response_modalities`.
- TTS uses text blocks with `annotations: [{"type": "speech_metadata", ...}]`.
  Single-speaker `speech_config` is a list; two-speaker config is
  `{"speakers": [...]}`. Every multi-speaker turn names a configured speaker.
- Transcription configuration belongs under
  `generation_config.transcription_config`. Verbatim options belong in
  `mode: {"type": "verbatim", ...}`; smart mode is the string `"smart"`.
- Parse every `model_output` step and its content, not only `output_image`,
  `output_audio`, or `output_text` convenience properties. Those can omit
  earlier interleaved output. Do not echo user input or thought steps.
- Unary Gemini 3.8 TTS defaults to WAV with an existing RIFF header. Save bytes
  unchanged. Raw L16, mu-law, and A-law must be explicitly requested.
- The server always sends `store=true` for Interactions generation and
  transcription. No tool exposes a storage toggle. Background execution and
  continuation use the retained interaction ID.

## Model-specific limits

- Images: at most 14 reference images. Nano Banana 2 supports 512, 1K, 2K, 4K;
  Lite supports only 1K and no search. Pro supports 1K, 2K, 4K.
- Omni: 3–10 second outputs, landscape/portrait, default 720p; 1080p/4K are
  upscaled. Uploaded videos for extension must be at most 10 seconds.
  Extension appends only to the end. Multi-turn generated-video extension can
  reach 40 seconds. Extending uploaded videos is currently unavailable in the
  EEA, Switzerland, and UK. Uploaded spoken dialogue cannot be extended with
  more speech; generated-video multi-turn speech extension is supported.
- Omni delivery defaults to URI; callers can request inline bytes. Interactions
  are always stored by the server.
- Omni URI delivery is recommended for videos over 4 MB. Poll the corresponding
  Files resource until ACTIVE before downloading. The guide warns that GET
  interaction responses currently return inline data even when creation used
  URI delivery.
- Transcribe: up to one hour of audio, or 30 minutes with diarization/timestamps.
  Up to eight speakers (three-plus attribution is experimental).
  Smart mode cannot use diarization or timestamps. Custom vocabulary has at most
  1,000 terms and cannot use diarization or timestamps.
- TTS: at most two configured speakers. Sustained style instructions are
  metadata, not spoken transcript text. Languages and voice IDs depend on the
  selected TTS tier and account access.
- Lyria: up to ten images, 44.1 kHz stereo music. Clip makes short MP3 clips;
  Lyria 3.5 makes full songs and supports WAV. Duration is directed by the prompt,
  not an invented duration field.

Model constraints that need media decoding (duration, speaker count in input
audio, regional eligibility) remain Google's responsibility. The server checks
request-level incompatibilities before sending a generation request.

The 10 MiB inline limit and 600-second media timeout are **server policies**,
not Google limits. Files upload bypasses the inline bound, subject to Google's
account and file limits.

Creation is not automatically retried. In google-genai 2.28, the Interactions
adapter interprets the shared retry `attempts` field differently from Files.
The server explicitly disables the Interactions retry strategy and tests that
retryable HTTP errors produce exactly one creation request. Retest this
compatibility workaround when upgrading the SDK.

## Separate APIs, deliberately not substituted

Omni is the only video-generation model/tool in this implementation. Live audio,
live transcription, Lyria RealTime, and creating or replicating voices use
separate APIs and are not included. Existing custom voices can be used by TTS.

## Refreshing this snapshot

1. Retrieve the current model catalog and relevant guides via Developer Knowledge.
2. Verify exact model IDs, Interactions support, and per-model limits.
3. Update `src/aio_gemini/catalog.py`, input validation, this file, and README.
4. Add real-SDK mock-transport tests for changed request/response fields.
5. Run Ruff, the full test suite (including stdio), and the package build.
   Live account access is a separate opt-in check and can incur charges.
