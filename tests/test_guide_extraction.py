import runpy
from pathlib import Path

import pytest

EXTRACTION = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/update_prompt_guides.py")
)


def test_heading_selection_keeps_exact_prose():
    text = "intro\n## Selected\n\nKeep **this** wording.\n\n## Next\nNot selected.\n"
    assert EXTRACTION["section"](text, "## Selected", "## Next") == (
        "## Selected\n\nKeep **this** wording."
    )
    with pytest.raises(ValueError):
        EXTRACTION["section"](text, "## Missing")


@pytest.mark.parametrize("language", ["Python", "JavaScript", "Java", "Go", "REST"])
def test_sdk_omission_preserves_prompt_template(language):
    text = (
        f"Prose.\n\n### Template\n\n```\nA [subject] in a [setting].\n```\n\n"
        f"### {language}\n\n```\nclient.call()\n```\n\nMore prose.\n"
    )
    result = EXTRACTION["without_sdk_samples"](text)
    assert "client.call()" not in result
    assert "A [subject] in a [setting]." in result
    assert "More prose." in result


@pytest.mark.parametrize(
    "code",
    [
        'input=[{"type": "text", "text": "Ask this EXACT question."}]',
        'prompt = "Ask this EXACT question."',
    ],
)
def test_prompt_string_extracted_without_rewriting(code):
    text = f"## Topic\n\nProse.\n\n### Python\n\n```\n{code}\n```\n## Next\n"
    assert EXTRACTION["with_prompt_example"](text, "## Topic", "## Next") == (
        "## Topic\n\nProse.\n\n```\nAsk this EXACT question.\n```"
    )


def test_image_embed_omission_does_not_rewrite_links_or_prose():
    text = (
        '![Example](https://example.test/img.png) <img src="img.png"> Original prose.'
    )
    assert EXTRACTION["without_images"](text) == "  Original prose."
