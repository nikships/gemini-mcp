# Official media prompting guides

Retrieved **2026-10-03** (image guide re-read **2026-10-06**) using the `retrieving-developer-knowledge` skill and
Google Developer Knowledge MCP. These are selected, near-verbatim documentation
excerpts, not generated summaries. The tools read packaged text using
`importlib.resources`, so they work from installed wheels without credentials,
network access, or the repository's working directory.

## Tools and sources

| `guide` value | Official source and included guidance |
| --- | --- |
| `image` | [Nano Banana image generation](https://ai.google.dev/gemini-api/docs/image-generation), the full prompting-strategies section (generation/editing templates, sample prompts, and best practices) plus the Google Search and Image Search grounding guidance |
| `video` | [Omni](https://ai.google.dev/gemini-api/docs/omni), the full Omni prompt guide: continuous shots, negatives, edits, audio, timing, text, extension, and media-role tags |
| `speech` | [Speech generation](https://ai.google.dev/gemini-api/docs/speech-generation), the full prompting guide: verbatim transcripts, styles, pauses, prosody, vocal tags, overlaps, consistency, and workflows |
| `music` | [Lyria prompt guide](https://ai.google.dev/gemini-api/docs/lyria-prompt-guide), all batch/shared prompting sections and Lyria 3.5 examples; [Music generation](https://ai.google.dev/gemini-api/docs/music-generation), best practices |
| `transcription` | [Transcription](https://ai.google.dev/gemini-api/docs/transcribe), overview, language hints, vocabulary, diarization, timestamps, modes, and best practices |

All guides are served by the single `get_prompt_guide` tool, which takes a
required `guide` argument.

Every result includes `sources[].markdown`, page titles/URLs, selected sections,
disclosed modifications, `retrieved_on`, related tools, current model choices,
attribution, license information, and separately labeled `mcp_notes`.

## Fidelity and boundaries

The guides preserve prose, prompt templates, lists, and textual examples.
It normalizes blank-line spacing, omits SDK code, and removes illustrative image
embeds and image-only comparison tables. It does not download or redistribute
source images, audio, or video. Examples that depend on those assets remain
examples; open the source page for their visual context.

The Lyria introduction and RealTime-only weighted-prompt/steering sections are
omitted because this server supports batch Interactions generation only.
Three rendered Lyria example strings had a leading `none `; this marker is
removed and the modification is recorded. No prompt directions are otherwise
rewritten or replaced with model-generated advice.

The official TTS guide mentions Voice design, replication, and the Extended Voice
Library. Those links and original instructions are preserved, but `mcp_notes`
make clear that this server only accepts existing voice IDs. It does not create,
clone, or search voices, or implement Live API streaming.

Transcribe is a configuration-driven ASR model with no free-form prompt argument.
Its guide does not invent a prompt interface. The notes map its API configuration
to `transcribe_audio` arguments and explain incompatible options.

Model lists in `PromptGuide.models` come from the current server catalog. Older
model names or other API capabilities in quoted source text are not model
fallbacks or promises of MCP support. The snapshots do not update automatically.

## Attribution and license

Portions of these guides are reproduced or modified from work created and
[shared by Google](https://developers.google.com/readme/policies) and used
according to terms described in the
[Creative Commons 4.0 Attribution License](https://creativecommons.org/licenses/by/4.0/).
The original source pages are linked above and in every tool result. Each source
records its modifications. No Google endorsement is implied.

Google's [Site Policies](https://developers.google.com/terms/site-policies)
explain the documentation license, attribution requirements, separate code-sample
license, and exclusions for trademarks and some media assets. These snapshots
include documentation and prompt text, not SDK source-code samples or binary
media assets.

## Refreshing the snapshots

Guides are maintained by hand. There is no extraction script.

1. Read the current source page with the Google Developer Knowledge MCP
   (`google-dev-docs` `get_documents`), using resource names such as
   `documents/ai.google.dev/gemini-api/docs/image-generation`. Long pages are
   saved to a tool-output file; read that file instead of relying on the
   truncated inline text.
2. Compare the page with the packaged Markdown in
   `src/aio_gemini/data/guides/<name>.md` and edit the file by hand. Copy
   Google's wording exactly. Omit SDK code samples, image embeds, and image-only
   tables. Do not add paraphrased or invented guidance to these files.
3. In `src/aio_gemini/data/guides/sources.json`, update that source's
   `retrieved_on`, `sections`, and `modifications` so they describe exactly what
   the file contains. Dates are per source, so only touch sources you re-read.
4. Put MCP-specific advice (parameter names, model limits in this tool) in
   `mcp_notes` in `src/aio_gemini/guides.py`, not in the Google excerpt.
5. Refresh the current model catalog separately if necessary. Update dates in
   documentation and tests, then run Ruff, the full test suite, and `uv build`.
   Verify the wheel and sdist include all guide resources.
