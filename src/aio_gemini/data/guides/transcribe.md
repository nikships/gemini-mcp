## Overview

Gemini 3.5 Transcribe is optimized for speech-to-text tasks. It handles diverse accents, background noise, and multi-language conversations.

Key capabilities include:

- **Automatic speech recognition (ASR):** Automatically detects languages across [85+ locales](https://ai.google.dev/gemini-api/docs/transcribe#supported-languages) . Handles intra-sentence and inter-sentential code-switching without manual configuration.
- **Custom vocabulary:** Biases recognition toward domain-specific terms, acronyms, and proper names by passing up to 1,000 phrases.
- **Speaker diarization:** Distinguishes between multiple speakers and attributes spoken segments to distinct labels.
- **Word-level timestamps:** Generates precise start and end time offsets for each recognized word.
- **Smart transcription:** Cleans up disfluencies, filler words, repetitions, and applies structured formatting.
- **Formatting and normalization:** Applies capitalization, punctuation, and inverse text normalization, such as converting "twenty six million dollars" to "\$26M".

For general audio reasoning or question answering over audio content, use [Audio understanding](https://ai.google.dev/gemini-api/docs/audio) . For text-to-speech audio synthesis, use [Text-to-speech](https://ai.google.dev/gemini-api/docs/speech-generation) .

## Language detection and hints

By default, the model detects the spoken language automatically. It switches between languages dynamically when speakers code-switch.

To use automatic detection, omit `language_codes` or provide an empty list:

If you know the language in advance, specify BCP-47 language codes in `language_codes` to improve transcription accuracy (see [Supported languages](https://ai.google.dev/gemini-api/docs/transcribe#supported-languages) ):

## Custom vocabulary

You can steer the speech model toward uncommon words, technical jargon, brand names, or proper nouns. Supply up to 1,000 terms in the `custom_vocabulary` array (best results are typically achieved with up to 100 terms):

> **Note:** You cannot combine `custom_vocabulary` with speaker diarization or word-level timestamps. The API rejects requests that include `custom_vocabulary` with either feature.

## Speaker diarization

Speaker diarization identifies different voices in the recording and tags each segment with a speaker identifier like `spk_1` or `spk_2` . Up to 8 speakers are supported (attribution for 3 or more speakers is experimental).

Enable diarization by configuring `diarization_mode` within `mode` :

## Word-level timestamps

Word-level timestamps provide exact start and end offsets for every recognized word in the audio stream.

> **Note:** Enabling word-level timestamps may degrade overall transcription accuracy.

Enable timestamps by configuring `timestamp_granularities` within `mode` :

You can combine `diarization_mode` and `timestamp_granularities` in `mode` to receive both speaker labels and word timestamps:

## Transcription modes

Gemini 3.5 Transcribe supports two transcription modes via the `mode` parameter:

- **`verbatim` (default)** : Returns an exact word-for-word transcript of everything spoken, preserving raw filler words ("um", "uh", "like", "you know"), repetitions, pauses, and false starts. Timestamps and speaker diarization are configured within this mode ( `{"type": "verbatim", ...}` ).
- **`smart` (Smart transcription)** : Optimizes the transcript for reading by applying intelligent post-processing:
  - **Disfluency removal** : Strips conversational filler words, stuttering, and false starts.
  - **Inline self-corrections** : Resolves spoken corrections directly (for example, *"Let's meet on Tuesday, actually no, Wednesday at two"* becomes *"Let's meet on Wednesday at 2:00 PM"* ).
  - **Automatic structured formatting** : Automatically structures spoken thoughts into paragraphs, numbered lists, bullet points, formatted dates, currencies, and numbers.
  - **Grammatical cleanup** : Applies natural punctuation, sentence casing, and flow.

| Spoken audio                                                                               | `verbatim` output                                                                    | `smart` (Smart transcription) output                       |
|--------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|------------------------------------------------------------|
| "Um, so for the meeting, I think we should, uh, invite Alice and, wait no, Bob and Carol." | "Um so for the meeting I think we should uh invite Alice and wait no Bob and Carol." | "For the meeting, I think we should invite Bob and Carol." |
| "First item review budget second item finalize timeline third item send recap"             | "first item review budget second item finalize timeline third item send recap"       | "1. Review budget 2. Finalize timeline 3. Send recap"      |

> **Note:** Smart transcription ( `"smart"` ) is incompatible with `timestamp_granularities` and `diarization_mode` . If you need word timestamps or speaker diarization, configure `mode` with `{"type": "verbatim", ...}` .

## Best practices

- **Provide clean audio:** Ensure audio recordings have clear voice separation and avoid severe clipping.
- **Provide language hints when known:** If you know the audio language in advance, specify `language_codes` to maximize accuracy.
- **Target custom vocabulary:** Include only distinct domain terms, brand names, or proper nouns in `custom_vocabulary` rather than common everyday words.
- **Use the Files API for large recordings:** For files longer than a few seconds, upload the file using `client.files.upload` and pass the returned file URI to the model.
