## Prompting guide

Gemini 3.8 TTS models treat input text strictly as a **verbatim transcript** . Unlike earlier preview models where stage directions were embedded in plain text, Gemini 3.8 TTS separates sustained turn-level directions ( `speech_metadata` ) from point-in-time inline vocal tags.

### Style field versus inline tags

Split your performance instructions by scope:

- **Turn-level delivery ( `speech_metadata.style` ):** Put sustained delivery attributes—such as emotion, prosody, overall pace, or delivery style (like `"whispering"` , `"out of breath"` , `"muttering"` , or `"sarcastic"` )—into the `style` field of `speech_metadata` . To create a stable character and performance across turns, design the persona upfront in [Voice design](https://ai.google.dev/gemini-api/docs/voice-design) and use `style` only for optional turn-level tweaks.
- **Point-in-time events (inline tags):** Put momentary non-speech vocal bursts, breaths, or pauses inline inside the transcript using angle brackets ( `<cough>` , `<breath>` , `<sigh>` , `<short pause>` ). Use angle brackets ( `<...>` ) for highest audio quality, and stick to human vocalizations rather than non-vocal sound effects.

| Scope                                         | Where to place               | Examples                                                                                 |
|-----------------------------------------------|------------------------------|------------------------------------------------------------------------------------------|
| **Turn-level** (sustained across the turn)    | `speech_metadata.style`      | `"angry tone"` , `"speaking rapidly"` , `"out of breath"` , `"whispers"` , `"sarcastic"` |
| **Point-in-time** (occurs at a specific word) | Inline in `text` ( `<...>` ) | `"<cough> Thank you all for coming tonight! <throat-clearing> As I was saying..."`       |

### Pacing and pauses

You can control rhythm and silence at three levels of granularity:

- **Punctuation and ellipses:** Use commas, dashes ( `--` ), and ellipses ( `...` ) for natural conversational hesitation.
- **Inline pause tags:** Insert `<short pause>` or `<long pause>` at exact points in the script where a speaker should pause: `text Hold on, let me think... <short pause> Alright, I've got it.`
- **Turn-level pace:** Set `"style": "speaking rapidly"` or `"style": "speaking slowly"` in `speech_metadata` to control the speaking rate across the whole turn.

### Prosody and pitch

Use **`speech_metadata.style`** to control prosody, pitch, and inflection across a turn (for example, `"style": "high pitch, cheerful and excited inflection"` or `"style": "monotone and flat"` ). If the emotion or prosody shifts mid-dialogue, split the script into separate turns with distinct `style` values for each turn.

### Emphasis

Capitalize specific words in the transcript, combined with punctuation and inline vocal tags, to place natural vocal stress on key words:

```
This is a VERY important point!
It was a VERY long day <sigh> ... nobody listens anymore.
```

### Vocal bursts and non-speech sounds

Place non-speech human vocalizations inline using angle brackets ( `<...>` ) at the exact point where the sound should occur. Recommended vocal tags include:

|                          |                 |                            |                               |
|--------------------------|-----------------|----------------------------|-------------------------------|
| `<argh>`                 | `<breath>`      | `<heavy breath>`           | `<exhales>`                   |
| `<cackle>`               | `<cheer>`       | `<chuckle>` / `<chuckles>` | `<cough>`                     |
| `<cry>`                  | `<gasp>`        | `<giggle>`                 | `<groan>`                     |
| `<growl>`                | `<grunt>`       | `<grr>`                    | `<hiss>`                      |
| `<laugh>` / `<laughter>` | `<moan>`        | `<pant>`                   | `<pff>` / `<phew>`            |
| `<scream>`               | `<shout>`       | `<shriek>`                 | `<sigh>` / `<sighs>`          |
| `<sneeze>`               | `<snicker>`     | `<snort>`                  | `<sob>`                       |
| `<throat-clearing>`      | `<tsk>`         | `<whimper>`                | `<whispers>` / `<whispering>` |
| `<yawn>`                 | `<short pause>` | `<long pause>`             |                               |

> **Note:** If your transcript is in a non-English language, continue to use English inline tags for best results.

### Backchannels and overlapping speech

In multi-speaker dialogue, wrap listener reactions in pipe characters ( `|reaction|` ) inside a speaker's turn to create natural backchannels or overlapping speech without breaking into a separate turn per reaction.

- **Short backchannel exchanges:** Layer brief listener reactions ( `|oh hmm|` , `|oh really?|` , `|absolutely|` ) inside the active speaker's turn:
  - **Turn 1 (Speaker A):** `"So the launch is Thursday |oh hmm| Are we actually ready?"`
  - **Turn 2 (Speaker B):** `"Ready enough |oh really?| The last blocker cleared this morning."`
  - **Turn 3 (Speaker A):** `"Then let's ship it |absolutely| and watch the dashboards."`
- **Overlapping and interleaved speech:** Use multiple pipe segments to simulate simultaneous or interleaved speech between two speakers (works best with `gemini-3.8-flash-tts` ):
  - **Simultaneous countdown/chorus:** `"Let's surprise him on three |ok| ready?"` followed by `"one. two. three. |happy| happy |birthday| birthday!"`
  - **Full speaker overlap:** `"Hello |oh| there |my| it |goodness| must |gracious| be |would| almost |you| time |look| for |at that| dinner"`

### Consistency across generations and what to avoid

Follow these guidelines to keep vocal identity stable across turns:

- **Design personas upfront in Voice design instead of long style blocks:** Long-form `"Audio Profile"` paragraphs and multi-bullet `"Director's Notes"` carried over from earlier models are the most common cause of voice drift. Use that same creative intuition upfront in [Voice design](https://ai.google.dev/gemini-api/docs/voice-design) to generate a persistent custom `voice_...` persona, then carry that voice ID through your TTS calls.
- **Rely on the voice reference for stability (omit meta-instructions):** Gemini 3.8 TTS models are trained to anchor on the audio reference first. Do not include instructions telling the model to hold the voice steady (such as `"do not switch speaker identity"` or `"maintain identical timbre"` )—extra prompt text increases drift. Drop unnecessary style instructions and let the model vary naturally around the stable point provided by the voice reference.
- **Do not try to change immutable speaker traits in `style` :** Avoid putting age, gender, names, or permanent accent changes in `speech_metadata.style` . Instead, pick a regional voice from the Extended Voice Library or create one with [Voice design](https://ai.google.dev/gemini-api/docs/voice-design) .

### Recommended workflow

1.  **Build the character once:** Create your character in [Voice design](https://ai.google.dev/gemini-api/docs/voice-design) or select a regional voice from the Extended Voice Library that matches your target language and persona.
2.  **Write natural spoken transcripts with disfluencies:** For maximum naturalness, write the `text` as a real spoken transcript—including natural conversational disfluencies and hesitations (for example, `"Oh uh yeah I think... hm, so that's interesting"` ).
3.  **Test plain TTS first:** Synthesize your transcript with an empty `style` field first—most requests need no `style` instruction at all.
4.  **Add short `style` prompts only for tweaks:** Add a concise `style` string (such as `"casual, friendly"` or `"muttering, then reassuring"` ) only for turns that need a specific delivery adjustment, and reuse that exact short string across turns when you want a consistent baseline.

### Multi-turn dialogue and voice agents

When building real-time conversational voice agents or multi-turn applications:

- Make **one TTS call per turn** as LLM text chunks arrive.
- Let the configured `voice` (prebuilt, designed `voice_...` , or replicated `voice_...` / `voicekey_...` ) carry the speaker's identity across turns—never re-send a long character persona on each turn.
- Leave the per-turn `style` field empty, or send one short constant string (such as `"casual, friendly"` ) for the whole conversation.
- Split long agent responses into shorter turns rather than reaching for stronger style prompts.
