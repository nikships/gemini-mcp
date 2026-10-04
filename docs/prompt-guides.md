# Official media prompting guides

Retrieved **2026-10-03** using the `retrieving-developer-knowledge` skill and
Google Developer Knowledge MCP. These are selected, near-verbatim documentation
excerpts, not generated summaries. The tools read packaged text using
`importlib.resources`, so they work from installed wheels without credentials,
network access, or the repository's working directory.

## Tools and sources

| `guide` value | Official source and included guidance |
| --- | --- |
| `image` | [Nano Banana image generation](https://ai.google.dev/gemini-api/docs/image-generation), the full prompting-strategies section: generation/editing templates, sample prompts, and best practices |
| `video` | [Omni](https://ai.google.dev/gemini-api/docs/omni), the full Omni prompt guide: continuous shots, negatives, edits, audio, timing, text, extension, and media-role tags |
| `speech` | [Speech generation](https://ai.google.dev/gemini-api/docs/speech-generation), the full prompting guide: verbatim transcripts, styles, pauses, prosody, vocal tags, overlaps, consistency, and workflows |
| `music` | [Lyria prompt guide](https://ai.google.dev/gemini-api/docs/lyria-prompt-guide), all batch/shared prompting sections and Lyria 3.5 examples; [Music generation](https://ai.google.dev/gemini-api/docs/music-generation), best practices |
| `transcription` | [Transcription](https://ai.google.dev/gemini-api/docs/transcribe), overview, language hints, vocabulary, diarization, timestamps, modes, and best practices |
| `analysis` | [Files](https://ai.google.dev/gemini-api/docs/files#prompt-guide), the full file-prompting strategies section, plus modality-specific sources below |

All guides are served by the single `get_prompt_guide` tool, which takes a
required `guide` argument. With `guide: "analysis"`, an optional `media_type` of
`"all"` (default), `"image"`, `"audio"`, `"video"`, or `"document"` selects the
modality sources; it is ignored for other guides. General Files guidance is always included.
Selected modality-specific sources:

- [Image understanding](https://ai.google.dev/gemini-api/docs/image-understanding):
  tips and best practices.
- [Audio understanding](https://ai.google.dev/gemini-api/docs/audio): overview,
  transcript prompting, timestamp prompting, and technical details. Exact prompt
  strings are extracted from SDK samples into standalone text blocks.
- [Video understanding](https://ai.google.dev/gemini-api/docs/video-understanding):
  static/agentic mode selection, conversation context, timestamp and detailed
  insight prompting, and technical details. Exact prompt strings are extracted
  into standalone text blocks.
- [Document understanding](https://ai.google.dev/gemini-api/docs/document-processing):
  introduction, PDF-versus-text behavior, and page-quality best practices.

Every result includes `sources[].markdown`, page titles/URLs, selected sections,
disclosed modifications, `retrieved_on`, related tools, current model choices,
attribution, license information, and separately labeled `mcp_notes`.

## Fidelity and boundaries

The extraction preserves prose, prompt templates, lists, and textual examples.
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

The retrieved image-understanding page recommends text before a single image,
while the Files guide recommends image first. Both statements remain unchanged.
The notes flag this discrepancy and state that `analyze_media` places media
before text. The Files guide also discusses sampling controls that
`analyze_media` does not expose. Video examples mention streaming and stateless
histories; this MCP instead supports stored continuation and background polling.

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

1. Retrieve the eleven source pages above with Developer Knowledge
   `get_documents`, using resource names such as
   `documents/ai.google.dev/gemini-api/docs/lyria-prompt-guide`.
2. Save the returned JSON exports locally. Each export must have the tool's
   `{"documents": [...]}` shape, with `name`, `uri`, `title`, and `content` per
   document. Do not include credentials or user-generated content.
3. From the repository, run the extraction with the actual retrieval date and
   absolute export paths:

   ```sh
   uv run python scripts/update_prompt_guides.py YYYY-MM-DD /ABSOLUTE/export1.json /ABSOLUTE/export2.json
   ```

   The script performs no network requests. It selects headings, applies only
   the documented transformations, and writes the packaged Markdown and
   `src/aio_gemini/data/guides/sources.json`. Missing headings or prompt samples
   fail before writing snapshots. Review changed source text, not only hashes.
4. Review all excerpts and scope notes. Update extraction boundaries if Google's
   headings change, and keep provenance/modification metadata accurate.
   `document_sha256` fingerprints each complete retrieved source;
   `excerpt_sha256` fingerprints the exact packaged excerpt.
5. Refresh the current model catalog separately if necessary. Update dates in
   documentation and tests, then run Ruff, the full test suite, and `uv build`.
   Verify the wheel and sdist include all guide resources.
