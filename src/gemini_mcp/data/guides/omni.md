## Gemini Omni Flash prompt guide

This section contains tips and examples on how to prompt Gemini Omni Flash effectively.

### Single scene

By default Omni Flash will try to create a video with a few different shots. It'll attempt to craft an interesting narrative based on the prompt.

If you need the output video to contain a single scene, you must prompt for that:

- In a single unbroken scene
- In a single continuous shot
- No scene cuts

For example:

```
Continuous, unbroken handheld shot of a fluffy tabby cat sitting on a sunny windowsill, looking out into a leafy garden. The cat's tail twitches slowly, and its ears rotate slightly toward ambient noises. Sunbeams illuminate dust motes in the air. Sound design: Gentle breeze, distant bird chirps. No dialogue.
```

### Removing unwanted elements

If the generated video contains things you don't want, include simple negative prompts to avoid them:

- No dialogue
- No embellishments
- No extra sound effects

### Prompts for editing

Simple prompts work best for video editing. Overly descriptive prompts can lead to unintended changes.

The following are more examples of simple editing prompts:

- Make this video anime
- Put a fashionable hat on this person
- Change the lighting to be more dramatic
- Change the text on the sign to say "Omni Flash"

When editing a specific aspect of the video, include `"Keep everything else the same"` to maintain visual consistency.

The following are some examples to show how to apply this technique:

- **Avoid:** `In the video of the man sitting on the sofa, please add a small black cat that runs from the right side of the screen, jumps onto his lap, and then he starts to stroke its head while looking down.`
  - **Simplify:** `Add a cat that jumps onto his lap, he begins to pet it. Keep everything else the same.`
- **Avoid:** `Please remove the cell phone that the person is holding in their hand and fill in the background so it looks like they are just holding their hand empty.`
  - **Simplify:** `Make the phone invisible. Keep everything else the same.`

### Prompting the audio

By default the model will try to generate an appropriate audio track for a video. This might not always be what you want. You can use your prompt to describe the type of audio you want. This is especially important if you want music in your video:

- Include calm background music
- The video has a high energy techno beat
- The audio is a low tinny radio broadcast in the background, playing a song

### Timing events

You can prompt for things to happen at specific times in the video, there is no precise syntax needed and you can use natural language. This is especially useful in creating your own scene cuts, rhythm or rapid fire sequences. See the following for examples:

- After 3 seconds, a woman enters the scene.
- At 5s the chorus starts in the background audio.
- Every 2s cut to a new frame.
- In a rapid fire sequence, every half a second (12 frames at 24fps) change the scene to a new location.

You can also use a timecode syntax:

```
[0-3s] A person is walking
[3-6s] They stop and turn around
[6-10s] They start running
```

### Meta prompting

You can ask Gemini Omni Flash to pay attention to general qualities or principles of video generation:

- Consider micro-detail, expression and timing to create a very rich, detailed but entirely natural scene.
- Be extremely detailed in your descriptions of characters and environments. Apply costume design principles to characters. Be very specific about the people, items and objects in the scene.
- Include plenty of appropriate detail in the background elements to make the scene feel realistic and natural.
- Make a rapid fire video that shows a different rare `[thing]` every 1s, upbeat music, include text to label the thing.

### Text in videos

You can prompt to include text in your video and Gemini Omni will render in a way that is correct and readable. If there will be naturally occurring text in your video, even in background elements, it can help to define what it should say.

- One word on the screen at a time: "did, you, know, that, Omni, can, do, awesome, text?" Each word appears for 1s with a different animated style. No dialogue.
- There is a street sign that says: "This is an AI generation by Omni", there is a storefront that says: "All you need AI", there's a car with the number plate: "OMNI1.1"

### Prompts for extending a video

With Gemini Omni 1.1 Flash you can extend videos with prompts like, `"Extend this video"` or `"The scene continues"` . You can extend videos by 10s, up to a total length of 40s.

Omni creates an extension that keeps video, motion, characters and audio coherent by using the last 10s of your original video as context. Some of the final frames in your input video will be edited to make the transition seamless.

When extending, all of this guide's Omni prompting tips still apply:

- Describe the audio in your extended scene, especially if you need it to change: `"The music continues into the chorus"`
- Describe if the scene continues, or if there is a shot cut to a new scene (perhaps with the same characters): `"Show the same characters in the next scene"`
- Include images and videos as references when extending to help keep your outputs accurate, or to introduce new characters: `"The person shown in the reference image enters the scene"` , `"The dog in the reference video <VIDEO_REF_0> jumps onto the sofa"`
- If using timestamps or a timecode syntax, 0s refers to the beginning of the extended part of the video. If extending a 10s video, the scene cut in this prompt will happen after 12s: `"After 2s cut to a new scene with the same characters"`

### Using tags in prompts to set image and video roles

You can use tags to bind uploaded media to specific generation roles. This lets you specify whether each image or video is a starting frame, a final frame, or a reference.

#### 1. Simple tags (recommended)

For simple cases where media roles are clear from the prompt, you can bind images and videos to roles directly:

- **`<FIRST_FRAME>`** : use the image as the starting frame of the video, for example: `<FIRST_FRAME> a woman is walking`
- **`<LAST_FRAME>`** : use the image as the final frame of the video to transition to. Must be used with `<FIRST_FRAME>` , for example: `<FIRST_FRAME> <LAST_FRAME> a woman is walking`
- **`<IMAGE_REF_N>`** : use the image as a reference, for example: `in the style of <IMAGE_REF_0> a woman <IMAGE_REF_1> is walking` (combines style reference from the first image and subject reference from the second image). Image references start from 0.
- **`<VIDEO_REF_N>`** : use the video as a character or object reference, for example: `the person in <VIDEO_REF_0> is playing the violin` . Video references also start from 0.

The following is an example with 6 reference images:

```
[0-3s] A studio fashion sequence. Starting with woman <IMAGE_REF_0>, she is holding <IMAGE_REF_1>
[3-6s] Then we see the man <IMAGE_REF_2> holding <IMAGE_REF_3>
[6-10s] And finally another woman <IMAGE_REF_4> who is holding <IMAGE_REF_5> while walking.
```

#### 2. Declaring sources and references

For more complex cases with multiple media inputs and multiple roles, you can use explicit prefix tags paired with natural language instructions. You should declare these sources and references at the start of your prompt.

- `[# Sources <FIRST_FRAME>@Image1]` will use the first image as the starting frame.
- `[# Sources <FIRST_FRAME>@Image1 <LAST_FRAME>@Image2]` will use the first image as the starting frame and the second image as the final frame.
- `[# Sources <FIRST_FRAME>@Image1 <LAST_FRAME>@Image1]` will use the first image as both the first frame and the last frame, creating a video that loops.
- `[# Sources <FIRST_FRAME>@Image1] [# References <IMAGE_REF_0>@Image2]` will use the first image as the starting frame and the second image as a reference.
- `[# Sources <VIDEO_0>@Video1]` will use the video as the primary source video to edit or modify.
- `[# Sources <PREVIOUS_VIDEO>@Video1]` will use the video from the previous turn to extend.
- `[# References <IMAGE_REF_0>@Image1]` will use the first image as a reference.
- `[# References <IMAGE_REF_1>@Image2]` will use the second image as a reference.
- `[# References <IMAGE_REF_0>@Image1 <IMAGE_REF_1>@Image2]` will use both images as references.
- `[# References <VIDEO_REF_0>@Video1]` will use the first video as a reference.
- `[# References <IMAGE_REF_0>@Image1 <VIDEO_REF_0>@Video1]` will use both an image and a video as a reference.

Add guiding instructions at the end of your prompt:

- For a starting frame: `"Use this image as the starting frame."`
- For a looping video via start and end frames: `"Use this image as the first frame and the last frame."`
- For reference images: `"Use the given image(s) as references for video generation. The images should not be used as literal initial frames."`
- For reference videos: `"Use the given video(s) as references. Do not use them as a source for video editing."`

Some examples of prompts with source and reference declarations:

**Starting frame combined with a reference image:**

```
[# Sources <FIRST_FRAME>@Image1] [# References <IMAGE_REF_0>@Image2] a woman <IMAGE_REF_0> is walking. Use Image1 as the starting frame. Use Image2 as a reference for the video generation.
```

**Character reference video combined with an object reference image:**

```
[# References <IMAGE_REF_0>@Image1 <VIDEO_REF_0>@Video1] The woman in <VIDEO_REF_0> is playing the violin shown in <IMAGE_REF_0>. Use Video1 as a character reference and Image1 as an object reference.
```
