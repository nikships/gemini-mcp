## Prompting guide and strategies

This section provides prompt examples and templates for common image generation and editing workflows. Each example includes a re-usable template and a sample prompt for the Interactions API.

### Prompts for generating images

The following examples show how to use text prompts to generate various types of images.

#### 1. Photorealistic scenes

Describe a scene in rich detail. The more specific you are, the more control you have over the results.

### Template

```
A photorealistic [type of shot] of a [subject description] in a [setting
description]. [Description of the light]. Shot from a [camera angle]
with a [lens type].
```

### Prompt

```
A photorealistic wide-angle shot of a vibrant coral reef teeming with tropical fish. Crystal-clear turquoise water with sunbeams filtering down from the surface, illuminating a sea turtle gliding gracefully over the coral. Shot from a low perspective with a wide-angle lens. Aspect ratio 16:9.
```

#### 2. Stylized illustrations & stickers

Describe the artistic style, subject, and medium. Be specific about the visual detail (bold lines, colors, etc.) for consistent results.

### Template

```
A [style] of a [subject, with details about accessories or actions]
doing [activity]. The design features [visual qualities, e.g., bold outlines,
cel-shading, etc.] and [color/background preference].
```

### Prompt

```
A kawaii-style sticker of a happy red panda wearing a tiny bamboo hat. It's munching on a green bamboo leaf. The design features bold, clean outlines, simple cel-shading, and a vibrant color palette. The background must be white.
```

#### 3. Accurate text in images

Gemini excels at rendering text. Be clear about the text, the font style (descriptively), and the overall design. Use Gemini 3 Pro Image for professional asset production.

### Template

```
Create a [image type] for [brand/concept] with the text "[text to render]"
in a [font style]. The design should be [style description], with a
[color scheme].
```

### Prompt

```
Create a modern, minimalist logo for a coffee shop called 'The Daily Grind'. The text should be in a clean, bold, sans-serif font. The color scheme is black and white. Put the logo in a circle. Use a coffee bean in a clever way.
```

#### 4. Product mockups & commercial photography

Perfect for creating clean, professional product shots for ecommerce, advertising, or branding.

### Template

```
A high-resolution, studio-lit product photograph of a [product description]
on a [background surface/description]. The lighting is a [lighting setup,
e.g., three-point softbox setup] to [lighting purpose]. The camera angle is
a [angle type] to showcase [specific feature]. Ultra-realistic, with sharp
focus on [key detail]. [Aspect ratio].
```

### Prompt

```
A high-resolution, studio-lit product photograph of a minimalist ceramic
coffee mug in matte black, presented on a polished concrete surface. The
lighting is a three-point softbox setup designed to create soft, diffused
highlights and eliminate harsh shadows. The camera angle is a slightly
elevated 45-degree shot to showcase its clean lines. Ultra-realistic, with
sharp focus on the steam rising from the coffee. Square image.
```

#### 5. Minimalist & negative space design

Excellent for creating backgrounds for websites, presentations, or marketing materials where text will be overlaid.

### Template

```
A minimalist composition featuring a single [subject] positioned in the
[bottom-right/top-left/etc.] of the frame. The background is a vast, empty
[color] canvas, creating significant negative space. Soft, subtle lighting.
[Aspect ratio].
```

### Prompt

```
A minimalist composition featuring a single, delicate red maple leaf
positioned in the bottom-right of the frame. The background is a vast, empty
off-white canvas, creating significant negative space for text. Soft,
diffused lighting from the top left. Square image.
```

#### 6. Sequential art (comic panel / storyboard)

Builds on character consistency and scene description to create panels for visual storytelling. For accuracy with text and storytelling ability, these prompts work best with Gemini 3 Pro and Gemini 3.1 Flash Image.

### Template

```
Make a 3 panel comic in a [style]. Put the character in a [type of scene].
```

### Prompt

```
Make a 3 panel comic in a gritty, noir art style with high-contrast black and white inks. Put the character in a humurous scene.
```

#### 7. Grounding with Google Search

Use Google Search to generate images based on recent or real-time information. This is useful for news, weather, and other time-sensitive topics.

### Prompt

```
Make a simple but stylish graphic of last night's Arsenal game in the Champion's League
```

### Prompts for editing images

These examples show how to provide images alongside your text prompts for editing, composition, and style transfer.

#### 1. Adding and removing elements

Provide an image and describe your change. The model will match the original image's style, lighting, and perspective.

### Template

```
Using the provided image of [subject], please [add/remove/modify] [element]
to/from the scene. Ensure the change is [description of how the change should
integrate].
```

### Prompt

```
"Using the provided image of my cat, please add a small, knitted wizard hat
on its head. Make it look like it's sitting comfortably and matches the soft
lighting of the photo."
```

#### 2. Inpainting (semantic masking)

Conversationally define a "mask" to edit a specific part of an image while leaving the rest untouched.

### Template

```
Using the provided image, change only the [specific element] to [new
element/description]. Keep everything else in the image exactly the same,
preserving the original style, lighting, and composition.
```

### Prompt

```
"Using the provided image of a living room, change only the blue sofa to be
a vintage, brown leather chesterfield sofa. Keep the rest of the room,
including the pillows on the sofa and the lighting, unchanged."
```

#### 3. Style transfer

Provide an image and ask the model to recreate its content in a different artistic style.

### Template

```
Transform the provided photograph of [subject] into the artistic style of [artist/art style]. Preserve the original composition but render it with [description of stylistic elements].
```

### Prompt

```
"Transform the provided photograph of a modern city street at night into the artistic style of Vincent van Gogh's 'Starry Night'. Preserve the original composition of buildings and cars, but render all elements with swirling, impasto brushstrokes and a dramatic palette of deep blues and bright yellows."
```

#### 4. Advanced composition: combining multiple images

Provide multiple images as context to create a new, composite scene. This is perfect for product mockups or creative collages.

### Template

```
Create a new image by combining the elements from the provided images. Take
the [element from image 1] and place it with/on the [element from image 2].
The final image should be a [description of the final scene].
```

### Prompt

```
"Create a professional e-commerce fashion photo. Take the blue floral dress
from the first image and let the woman from the second image wear it.
Generate a realistic, full-body shot of the woman wearing the dress, with
the lighting and shadows adjusted to match the outdoor environment."
```

#### 5. High-fidelity detail preservation

To ensure critical details (like a face or logo) are preserved during an edit, describe them in great detail along with your edit request.

### Template

```
Using the provided images, place [element from image 2] onto [element from
image 1]. Ensure that the features of [element from image 1] remain
completely unchanged. The added element should [description of how the
element should integrate].
```

### Prompt

```
"Take the first image of the woman with brown hair, blue eyes, and a neutral
expression. Add the logo from the second image onto her black t-shirt.
Ensure the woman's face and features remain completely unchanged. The logo
should look like it's naturally printed on the fabric, following the folds
of the shirt."
```

#### 6. Bring something to life

Upload a rough sketch or drawing and ask the model to refine it into a finished image.

### Template

```
Turn this rough [medium] sketch of a [subject] into a [style description]
photo. Keep the [specific features] from the sketch but add [new details/materials].
```

### Prompt

```
"Turn this rough pencil sketch of a futuristic car into a polished photo of the finished concept car in a showroom. Keep the sleek lines and low profile from the sketch but add metallic blue paint and neon rim lighting."
```

#### 7. Character consistency: 360 view

You can generate 360-degree views of a character by iteratively prompting for different angles. For best results, include previously generated images in subsequent prompts to maintain consistency. For complex poses, include a reference image of the selected pose.

### Template

```
A studio portrait of [person] against [background], [looking forward/in profile looking right/etc.]
```

### Prompt

```
A studio portrait of this man against white, in profile looking right
```

### Best practices

To elevate your results from good to great, incorporate these professional strategies into your workflow.

- **Be hyper-specific:** The more detail you provide, the more control you have. Instead of "fantasy armor," describe it: "ornate elven plate armor, etched with silver leaf patterns, with a high collar and pauldrons shaped like falcon wings."
- **Provide context and intent:** Explain the *purpose* of the image. The model's understanding of context will influence the final output. For example, "Create a logo for a high-end, minimalist skincare brand" will yield better results than just "Create a logo."
- **Iterate and refine:** Don't expect a perfect image on the first try. Use the conversational nature of the model to make small changes. Follow up with prompts like, "That's great, but can you make the lighting a bit warmer?" or "Keep everything the same, but change the character's expression to be more serious."
- **Use step-by-step instructions:** For complex scenes with many elements, break your prompt into steps. "First, create a background of a serene, misty forest at dawn. Then, in the foreground, add a moss-covered ancient stone altar. Finally, place a single, glowing sword on top of the altar."
- **Use "semantic negative prompts":** Instead of saying "no cars," describe the intended scene positively: "an empty, deserted street with no signs of traffic."
- **Control the camera:** Use photographic and cinematic language to control the composition. Terms like `wide-angle shot` , `macro shot` , `low-angle perspective` .

## Grounding with Google Search: when to use it

- **Grounding with Google Search** : The model can use Google Search as a tool to verify facts and generate imagery based on real-time data (e.g., current weather maps, stock charts, recent events).
  - **Not supported by Gemini 3.1 Flash Lite Image model.**
  - **Gemini Nano Banana 2.1 and Gemini 3.1 Flash Image** add the integration of Google Image Search Grounding alongside Web Search.

### Grounding with Google Search

Use the [Google Search tool](https://ai.google.dev/gemini-api/docs/google-search) to generate images based on real-time information, such as weather forecasts, stock charts, or recent events.

Note that when using Grounding with Google Search with image generation, image-based search results are not passed to the generation model and are excluded from the response (see [Grounding with Google Image Search](https://ai.google.dev/gemini-api/docs/image-generation#image-search) )

The response includes `google_search_call` and `google_search_result` steps, along with inline `url_citation` annotations on the text step:

- **`google_search_result`** : Contains `search_suggestions` , an HTML snippet for rendering search suggestions in your UI.
- **`url_citation` annotations** : Inline citations on the text step linking parts of the response to their web sources.

### Grounding with Google Search for images (Nano Banana 2.1 and 3.1 Flash)

> **Note:** This feature is only available for the Gemini Nano Banana 2.1 and Gemini 3.1 Flash Image models.

Grounding with Google Image Search allows models to use web images retrieved via Google Image Search as visual context for image generation. Image Search is a new search type within the existing Grounding with Google Search tool, functioning alongside standard [Web Search](https://ai.google.dev/gemini-api/docs/image-generation#use-with-grounding) .

To enable Image Search, configure the `google_search` tool in your API request and specify `image_search` within the `search_types` array. Image Search can be used independently or together with Web Search.

**Display requirements**

When you use Image Search within Grounding with Google Search, you must display the `search_suggestions` from the `google_search_result` step. Full usage requirements are detailed in the [Terms of Service](https://ai.google.dev/gemini-api/terms#grounding-with-google-search) .

**Response**

For grounded responses using image search, the API returns inline citations and attribution metadata as part of the response steps:

- **`url_citation` annotations** : Inline citations on the text content block within `model_output` , linking the generated content to its source.

- **`google_search_result`** : Contains `search_suggestions` , an HTML snippet for rendering search suggestions in your UI.

### Example prompts that use search

These prompts come from Google's examples. The first uses image search and was generated with Nano Banana 2; the second and third use search and were generated with Nano Banana Pro.

```
Use image search to find accurate images of a resplendent quetzal bird. Create a beautiful 3:2 wallpaper of this bird, with a natural top to bottom gradient and minimal composition.
```

```
Use search to find how the Gemini 3 Flash launch has been received. Use this information to write a short article about it (with headings). Return a photo of the article as it appeared in a design focused glossy magazine. It is a photo of a single folded over page, showing the article about Gemini 3 Flash. One hero photo. Headline in serif.
```

```
Present a clear, 45° top-down isometric miniature 3D cartoon scene of London, featuring its most iconic landmarks and architectural elements. Use soft, refined textures with realistic PBR materials and gentle, lifelike lighting and shadows. Integrate the current weather conditions directly into the city environment to create an immersive atmospheric mood. Use a clean, minimalistic composition with a soft, solid-colored background. At the top-center, place the title "London" in large bold text, a prominent weather icon beneath it, then the date (small text) and temperature (medium text). All text must be centered with consistent spacing, and may subtly overlap the tops of the buildings.
```

### Limitations that affect grounding

- `gemini-nano-banana-2.1` and `gemini-3.1-flash-image` Grounding with Google Search do not support using real-world images of people from web search at this time.
