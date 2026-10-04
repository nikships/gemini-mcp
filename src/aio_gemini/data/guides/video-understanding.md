## Agentic video understanding

By default, video inputs use static processing (extracting frames at 1 FPS). Gemini 3.8 Flash, 3.7 Flash, 3.6 Flash, and 3.5 Flash Lite models also support **agentic video understanding** , where the model dynamically explores the video timeline, selectively inspecting transcripts and adaptively adjusting frame rates and resolution on the fly based on the prompt.

| **Mode**             | **Description**                                                                                                                                                                         | **Supported models**                                   |
|----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------|
| **Static** (default) | Extracts frames at a fixed rate (1 FPS) and places them into context in a single pass. Works well for short clips.                                                                      | All Gemini models                                      |
| **Agentic**          | The model dynamically navigates the video timeline, loading only the content it needs based on the prompt. Up to 88% more token-efficient and \~7% higher quality on long-form content. | Gemini 3.8 Flash, 3.7 Flash, 3.6 Flash, 3.5 Flash Lite |

### Choose a processing mode

As a general guideline, start with **agentic** mode, especially when optimizing for response quality or token efficiency.

- **Agentic:** Long-form videos or queries targeting specific moments. The model dynamically navigates the timeline to target contextually relevant information without filling the context window.
- **Static:** Latency-sensitive queries on short clips (under 5 minutes), or cases where frame-level precision across the entire clip is needed.

> **Note:** For long videos or complex prompts where agentic processing takes more time, use streaming ( `stream=True` ) or background execution ( `background=True` ). This keeps the connection active, surfaces intermediate reasoning steps, and avoids connection or authentication timeouts.

### Multi-turn video conversations

Video context is preserved across turns in a conversation. When using agentic processing:

- **Stateful mode** (using `previous_interaction_id` ): The server retains the video context. No additional handling is needed.
- **Stateless mode** (using `step_list` ): In stateless mode, the response includes `processing_call` and `processing_result` steps that encode the video context. You must include all steps from the response in your next request's `step_list` to preserve video context. While omitting them does not currently return an API error, the video context is lost, significantly reducing response quality on follow-up questions. Note that returned steps sent in subsequent requests contribute to input token counts.

## Refer to timestamps in the content

You can ask questions about specific points in time within the video using timestamps of the form `MM:SS` .

```
What are the examples given at 00:05 and 00:10 supposed to show us?
```

## Extract detailed insights from video

Gemini models offer powerful capabilities for understanding video content by processing information from both the **audio and visual** streams. This lets you extract a rich set of details, including generating descriptions of what is happening in a video and answering questions about its content.

For visual descriptions, the model samples the video at a rate of **1 frame per second** (FPS). This default sampling rate works well for most content, but note that it may miss details in videos with rapid motion or quick scene changes.

```
Describe the key events in this video, providing both audio and visual details. Include timestamps for salient moments.
```

## Technical details about videos

- **Supported models and context** : All Gemini models can process video data.
  - Models with a 1M context window can process videos up to 3 hours long by default (at low media resolution), or up to 1 hour long at high media resolution.
- **Processing modes** : Gemini 3.8 Flash, 3.7 Flash, 3.6 Flash, 3.5 Flash Lite, and later models support two video processing modes:
  - **Static** : Frames are extracted at 1 FPS and placed into context (default for all models). Audio is processed at 1Kbps (single channel). Timestamps are added every second. Best for short clips or when every frame matters (such as frame-by-frame inspection). Note that fast action sequences might lose detail due to the 1 FPS sampling rate.
  - **Agentic** : The model dynamically navigates the video, loading transcript and/or frames and/or audio on demand. This uses up to 88% fewer tokens for long-form content, though navigation may slightly increase Time to First Token (TTFT) on short clips (\<5 minutes) due to internal reasoning and tool round-trips before generation begins. Best for long-form videos to optimize token costs and response quality. Supported on Gemini 3.8 Flash, 3.7 Flash, 3.6 Flash, and 3.5 Flash Lite. See [Agentic video understanding](https://ai.google.dev/gemini-api/docs/video-understanding#agentic-video-understanding) for details.
- **Token calculation (static mode)** : Each second of video is tokenized as follows:
  - Individual frames (sampled at 1 FPS):
    - If `media_resolution` is set to low, frames are tokenized at 66 tokens per frame.
    - Otherwise, frames are tokenized at 258 tokens per frame.
  - Audio: 32 tokens per second.
  - Metadata is also included.
  - Total: Approximately 100 tokens per second of video at default (low) media resolution, or approximately 300 tokens per second of video at high media resolution.
- **Token calculation (agentic mode)** : Token usage varies based on content complexity and the model's navigation strategy. Navigation reasoning tokens generated during video exploration are accounted as **thought tokens** ( `total_thought_tokens` ), while frames, audio, and transcript loaded on demand are accounted as tool use tokens ( `total_tool_use_tokens` ). Agentic processing typically uses up to 88% fewer total tokens than static processing for long-form content because the model loads only the transcript and/or frames and/or audio it needs to answer the prompt (see the [tokens guide](https://ai.google.dev/gemini-api/docs/tokens#video-token-usage) ).
- **Media resolution** : Gemini 3 introduces granular control over multimodal vision processing with the `media_resolution` parameter. The `media_resolution` parameter determines the **maximum number of tokens allocated per input image or video frame.** Higher resolutions improve the model's ability to read fine text or identify small details, but increase token usage and latency. The `media_resolution` and `processing` parameters are independent: you can set both on the same video input.

For more details on token calculations, see the [tokens](https://ai.google.dev/gemini-api/docs/tokens) guide.

- **Timestamp format** : When referring to specific moments in a video within your prompt, use the `MM:SS` format (e.g., `01:15` for 1 minute and 15 seconds).
- **Prompt placement** : If combining text and a single video, place the text prompt *after* the video part in the `input` array.
- **Timeouts for long requests** : For videos that require extended processing time or complex multi-step reasoning, use streaming ( `stream=True` ) or background execution ( `background=True` ). Synchronous, non-streaming requests that experience backend retries under high demand can exceed connection or authentication token validity windows, which may surface as unexpected `401 Unauthorized` or timeout errors. Streaming keeps the connection active and surfaces intermediate reasoning and tool call progress.
