"""Extract attributed prompt-guide snapshots from Developer Knowledge JSON exports.

Usage: python scripts/update_prompt_guides.py YYYY-MM-DD /ABSOLUTE/export.json ...
No network calls. Review the resulting diff before accepting refreshed guidance.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "src/gemini_mcp/data/guides"
LANGUAGES = r"Python|JavaScript|Java|Go|REST"


def section(text: str, start: str, end: str | None = None) -> str:
    """Select a heading-delimited excerpt without rewriting the text."""
    offset = text.index(start + "\n")
    limit = text.index(end + "\n", offset + len(start)) if end else len(text)
    return text[offset:limit].strip()


def without_sdk_samples(text: str) -> str:
    return re.sub(
        rf"(?ms)^### (?:{LANGUAGES})\n\n```[^\n]*\n.*?^```\n?",
        "",
        text,
    )


def without_images(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    return re.sub(r"<img\b[^>]*>", "", text)


def normalize_spacing(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def with_prompt_example(text: str, start: str, end: str) -> str:
    """Retain section prose and the first exact prompt, without copying SDK code."""
    selected = section(text, start, end)
    prose = selected.split("### Python\n", 1)[0].strip()
    prompt = re.search(r'(?:"text"\s*:|prompt\s*=)\s*"([^"\n]+)"', selected)
    if prompt is None:
        raise ValueError(f"No prompt example found for {start}")
    return f"{prose}\n\n```\n{prompt[1]}\n```"


def extract(documents: dict[str, dict], retrieved_on: str) -> dict:
    manifest = {
        "retrieved_on": retrieved_on,
        "attribution": (
            "Portions of these guides are reproduced or modified from work created "
            "and shared by Google (https://developers.google.com/readme/policies) "
            "and used according to the Creative Commons 4.0 Attribution License "
            "(https://creativecommons.org/licenses/by/4.0/). Source links and "
            "modifications are listed with each excerpt."
        ),
        "license": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "sources": {},
    }
    excerpts = {}

    def save(name: str, headings: list[str], text: str, modifications: list[str]):
        document = documents[name]
        markdown = normalize_spacing(text)
        manifest["sources"][name] = {
            "title": document["title"],
            "url": document["uri"],
            "sections": headings,
            "modifications": [
                "Selected sections only; unrelated API reference material omitted.",
                "Normalized blank-line spacing in the Developer Knowledge rendering.",
                *modifications,
            ],
            "document_sha256": hashlib.sha256(
                document["content"].encode("utf-8")
            ).hexdigest(),
            "excerpt_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        }
        excerpts[name] = markdown

    image = documents["image-generation"]["content"]
    image = without_sdk_samples(
        section(image, "## Prompting guide and strategies", "## Limitations")
    )
    # The input/output comparison tables contain only visual examples.
    image = re.sub(
        r"(?m)^(?:\|[^\n]*\n)+",
        lambda match: "" if "![" in match[0] else match[0],
        image,
    )
    save(
        "image-generation",
        ["Prompting guide and strategies"],
        without_images(image),
        ["Omitted SDK code, illustrative images, and image-only comparison tables."],
    )
    save(
        "omni",
        ["Gemini Omni Flash prompt guide"],
        section(
            documents["omni"]["content"],
            "## Gemini Omni Flash prompt guide",
            "## What's next",
        ),
        [],
    )
    save(
        "speech-generation",
        ["Prompting guide"],
        section(
            documents["speech-generation"]["content"],
            "## Prompting guide",
            "## Limitations",
        ),
        [],
    )
    music = documents["lyria-prompt-guide"]["content"]
    music = (
        section(music, "## Prompt fundamentals", "## Prompting Lyria RealTime")
        + "\n\n"
        + section(
            music, "### Lyria 3.5 examples", "### Lyria RealTime steering set"
        ).replace("`none ", "`")
    )
    save(
        "lyria-prompt-guide",
        [
            "Prompt fundamentals",
            "Genre and style",
            "Instruments and textures",
            "Song structure and timing",
            "Lyrics and vocals",
            "Musical parameters",
            "Lyria 3.5 examples",
        ],
        music,
        [
            "Omitted the introduction and RealTime-only weighted-prompt/"
            "steering sections.",
            "Removed the leading 'none ' from three rendered example prompt strings.",
        ],
    )
    save(
        "music-generation",
        ["Best practices"],
        section(
            documents["music-generation"]["content"],
            "## Best practices",
            "## Limitations",
        ),
        [],
    )
    asr = documents["transcribe"]["content"]
    asr_headings = [
        ("## Overview", "## Language detection and hints"),
        ("## Language detection and hints", "## Custom vocabulary"),
        ("## Custom vocabulary", "## Speaker diarization"),
        ("## Speaker diarization", "## Word-level timestamps"),
        ("## Word-level timestamps", "## Transcription modes"),
        ("## Transcription modes", "## Parsing transcription output"),
        ("## Best practices", "## Limitations"),
    ]
    save(
        "transcribe",
        [start.removeprefix("## ") for start, _ in asr_headings],
        "\n\n".join(without_sdk_samples(section(asr, a, b)) for a, b in asr_headings),
        ["Omitted SDK code samples; configuration guidance is preserved."],
    )
    save(
        "files",
        ["File prompting strategies"],
        without_images(
            section(
                documents["files"]["content"],
                "## File prompting strategies",
                "## What's next",
            )
        ),
        [
            "Omitted illustrative image embeds; example prompts and responses "
            "are preserved."
        ],
    )
    save(
        "image-understanding",
        ["Tips and best practices"],
        section(
            documents["image-understanding"]["content"],
            "## Tips and best practices",
            "## What's next",
        ),
        [],
    )
    audio = documents["audio"]["content"]
    save(
        "audio",
        [
            "Overview",
            "Get a transcript",
            "Refer to timestamps",
            "Technical details about audio",
        ],
        "\n\n".join(
            [
                section(audio, "## Overview", "## Transcribe speech to text"),
                with_prompt_example(
                    audio, "## Get a transcript", "## Refer to timestamps"
                ),
                with_prompt_example(audio, "## Refer to timestamps", "## Count tokens"),
                section(audio, "## Technical details about audio", "## What's next"),
            ]
        ),
        [
            "Extracted exact prompt strings from SDK samples into standalone "
            "text blocks."
        ],
    )
    video = documents["video-understanding"]["content"]
    save(
        "video-understanding",
        [
            "Agentic video understanding",
            "Choose a processing mode",
            "Multi-turn video conversations",
            "Refer to timestamps in the content",
            "Extract detailed insights from video",
            "Technical details about videos",
        ],
        "\n\n".join(
            [
                section(
                    video,
                    "## Agentic video understanding",
                    "### Set the processing mode",
                ),
                section(
                    video,
                    "### Multi-turn video conversations",
                    "## Refer to timestamps in the content",
                ),
                with_prompt_example(
                    video,
                    "## Refer to timestamps in the content",
                    "## Extract detailed insights from video",
                ),
                with_prompt_example(
                    video,
                    "## Extract detailed insights from video",
                    "## Customize video processing",
                ),
                section(video, "## Technical details about videos", "## What's next"),
            ]
        ),
        [
            "Extracted exact prompt strings from SDK samples into standalone "
            "text blocks."
        ],
    )
    document = documents["document-processing"]["content"]
    save(
        "document-processing",
        ["Introduction", "Document types", "Best practices"],
        document[: document.index("## Passing PDF data inline")].strip()
        + "\n\n"
        + section(document, "### Document types", "## What's next"),
        [],
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, markdown in excerpts.items():
        OUTPUT.joinpath(f"{name}.md").write_text(markdown, encoding="utf-8")
    return manifest


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(
            "Usage: update_prompt_guides.py YYYY-MM-DD /ABSOLUTE/export.json ..."
        )
    documents = {}
    for export in sys.argv[2:]:
        for document in json.loads(Path(export).read_text(encoding="utf-8"))[
            "documents"
        ]:
            documents[document["name"].rsplit("/", 1)[-1]] = document
    manifest = extract(documents, sys.argv[1])
    OUTPUT.joinpath("sources.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Extracted {len(manifest['sources'])} official guide sources to {OUTPUT}")
