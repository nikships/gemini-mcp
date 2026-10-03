"""Exercise the real SDK against a local mock transport, never the Google API."""

import json

import httpx
import pytest
from fastmcp.exceptions import ToolError

from gemini_mcp import server


async def test_real_sdk_posts_interactions(sdk_transport):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "real-sdk-id",
                "status": "completed",
                "steps": [
                    {
                        "type": "model_output",
                        "content": [
                            {"type": "text", "text": "Hello"},
                            {"type": "text", "text": "!"},
                        ],
                    }
                ],
            },
        )

    sdk_transport(handle)
    result = await server.generate_text(
        "Say hello",
        system_instruction="Be brief",
        max_output_tokens=123,
        previous_interaction_id="prior-turn",
        store=True,
    )
    assert result.model_dump() == {
        "id": "real-sdk-id",
        "status": "completed",
        "text": "Hello!",
    }
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url.path.endswith("/interactions")
    body = json.loads(request.content)
    assert body["model"] == server.DEFAULT_MODEL
    assert body["input"] == "Say hello"
    assert body["system_instruction"] == "Be brief"
    assert body["generation_config"]["max_output_tokens"] == 123
    assert body["previous_interaction_id"] == "prior-turn"
    assert body["store"] is True
    assert body["stream"] is False
    assert body["background"] is False


async def test_real_sdk_error_is_redacted(sdk_transport):
    def handle(request):
        return httpx.Response(
            400,
            json={"error": {"code": 400, "message": "sensitive-upstream-detail"}},
        )

    sdk_transport(handle)
    with pytest.raises(ToolError, match="HTTP 400") as exc:
        await server.generate_text("Hello")
    assert "sensitive-upstream-detail" not in str(exc.value)


@pytest.mark.parametrize("status", [429, 500, 503])
@pytest.mark.parametrize("tool", [server.generate_text, server.generate_image])
async def test_generation_errors_do_not_retry_or_fallback(sdk_transport, status, tool):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(
            status,
            json={"error": {"code": status, "message": "sensitive-detail"}},
        )

    sdk_transport(handle)
    with pytest.raises(ToolError, match=f"HTTP {status}"):
        await tool("Hello")
    assert len(requests) == 1
