## Overview

Gemini can analyze and understand audio input and generate text responses, enabling use cases like:

- Describe, summarize, or answer questions about audio content
- Transcription and translation (speech to text)
- Speaker diarization (identifying different speakers)
- Emotion detection in speech and music
- Analyzing specific segments with timestamps

For real-time voice and video interactions, see the [Live API](https://ai.google.dev/gemini-api/docs/live) . For dedicated speech to text models with support for real-time transcription, use the [Google Cloud Speech-to-Text API](https://cloud.google.com/speech-to-text) .

## Get a transcript

To get a transcript, ask for it in the prompt:

```
Generate a transcript of the speech.
```

## Refer to timestamps

Use `MM:SS` format to reference specific sections:

```
Provide a transcript from 02:30 to 03:29.
```

## Technical details about audio

- **Tokens** : 32 tokens per second of audio (1 minute = 1,920 tokens)
- **Non-speech** : Gemini understands non-speech sounds (birdsong, sirens, etc.)
- **Max length** : 9.5 hours of audio per prompt
- **Resolution** : Downsampled to 16 Kbps
- **Channels** : Multi-channel audio combined to single channel
