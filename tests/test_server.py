from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from google.genai import interactions

from aio_gemini import server


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def google(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    models = SimpleNamespace(generate_content=AsyncMock())
    interaction_api = SimpleNamespace(
        sdk_configuration=SimpleNamespace(
            retry_config=SimpleNamespace(strategy="default")
        ),
        create=AsyncMock(
            return_value=interactions.Interaction.model_validate(
                {
                    "id": "interaction-123",
                    "status": "completed",
                    "steps": [
                        {
                            "type": "model_output",
                            "content": [{"type": "text", "text": "Hello!"}],
                        }
                    ],
                }
            )
        ),
    )
    async_client = MagicMock()
    async_client.__aenter__.return_value = SimpleNamespace(
        models=models, interactions=interaction_api
    )
    sync_client = MagicMock()
    sync_client.__enter__.return_value = sync_client
    sync_client.aio = async_client
    factory = MagicMock(return_value=sync_client)
    monkeypatch.setattr(server.genai, "Client", factory)
    return SimpleNamespace(
        models=models,
        interactions=interaction_api,
        factory=factory,
        sync=sync_client,
        aio=async_client,
    )


async def test_client_cleanup(google):
    result = await server.generate_image("Draw a cat")
    assert result.id == "interaction-123"
    assert result.status == "completed"
    assert result.text == "Hello!"
    kwargs = google.interactions.create.call_args.kwargs
    assert kwargs["store"] is True
    assert kwargs["stream"] is False
    assert kwargs["background"] is False
    assert kwargs["previous_interaction_id"] is None
    google.models.generate_content.assert_not_awaited()
    assert google.factory.call_args.kwargs["http_options"].timeout == 600_000
    assert google.factory.call_args.kwargs["vertexai"] is False
    assert google.factory.call_args.kwargs["enterprise"] is False
    google.aio.__aexit__.assert_awaited_once()
    google.sync.__exit__.assert_called_once()


async def test_api_key_precedence_and_fallback(google, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "fallback-key")
    await server.generate_image("Hello")
    assert google.factory.call_args.kwargs["api_key"] == "test-key"
    monkeypatch.setenv("GEMINI_API_KEY", " ")
    await server.generate_image("Hello")
    assert google.factory.call_args.kwargs["api_key"] == "fallback-key"


async def test_missing_key():
    with pytest.raises(ToolError, match="Set GEMINI_API_KEY or GOOGLE_API_KEY"):
        await server.generate_image("Hello")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"prompt": " "},
        {"prompt": "Hi", "previous_interaction_id": " "},
    ],
)
async def test_blank_inputs(google, kwargs):
    with pytest.raises(ToolError, match="must not be blank"):
        await server.generate_image(**kwargs)
    google.factory.assert_not_called()


async def test_no_text_response_preserves_metadata(google):
    google.interactions.create.return_value = interactions.Interaction(
        id="empty-interaction", status="completed"
    )
    result = await server.generate_image("Hello")
    assert (result.id, result.status, result.text) == (
        "empty-interaction",
        "completed",
        "",
    )


async def test_incomplete_response_status(google):
    google.interactions.create.return_value = interactions.Interaction(
        id="partial-interaction", status="incomplete"
    )
    assert (await server.generate_image("Hello")).status == "incomplete"


async def test_api_errors_are_redacted(google):
    google.interactions.create.side_effect = server.interaction_errors.APIStatusError(
        "sensitive-upstream-detail",
        response=httpx.Response(
            429,
            request=httpx.Request("POST", "https://example.test/interactions"),
        ),
        body={"sensitive": "upstream-detail"},
    )
    with pytest.raises(ToolError, match="HTTP 429") as exc:
        await server.generate_image("Hello")
    assert "sensitive-upstream-detail" not in str(exc.value)
    assert exc.value.__suppress_context__
    google.aio.__aexit__.assert_awaited_once()
    google.sync.__exit__.assert_called_once()


async def test_network_error_is_redacted(google):
    google.interactions.create.side_effect = httpx.ConnectError("sensitive-request-url")
    with pytest.raises(ToolError, match="Could not reach") as exc:
        await server.generate_image("Hello")
    assert "sensitive-request-url" not in str(exc.value)


async def test_mcp_discovery_and_generation(google):
    async with Client(server.create_server()) as client:
        names = {tool.name for tool in await client.list_tools()}
        assert "generate_image" in names
        assert "generate_text" not in names
        result = await client.call_tool("generate_image", {"prompt": "Hi"})
        assert result.structured_content["id"] == "interaction-123"
        assert result.structured_content["text"] == "Hello!"
        await client.call_tool(
            "generate_image",
            {
                "prompt": "Continue",
                "previous_interaction_id": result.data.id,
            },
        )
        assert google.interactions.create.call_args.kwargs["store"] is True
        assert (
            google.interactions.create.call_args.kwargs["previous_interaction_id"]
            == "interaction-123"
        )
        google.models.generate_content.assert_not_awaited()


@pytest.mark.parametrize("kind", ["connection", "timeout", "unknown"])
async def test_interactions_errors_are_redacted(google, kind):
    request = httpx.Request("POST", "https://example.test/interactions")
    if kind == "connection":
        error = server.interaction_errors.APIConnectionError(
            request=request, message="sensitive-upstream-detail"
        )
    elif kind == "timeout":
        error = server.interaction_errors.APITimeoutError(request=request)
    else:
        error = server.interaction_errors.APIError(
            "sensitive-upstream-detail", request=request, body=None
        )
    google.interactions.create.side_effect = error
    with pytest.raises(ToolError) as exc:
        await server.generate_image("Hello")
    assert "sensitive-upstream-detail" not in str(exc.value)
    assert exc.value.__suppress_context__
    google.aio.__aexit__.assert_awaited_once()
    google.sync.__exit__.assert_called_once()


@pytest.mark.parametrize(
    "arguments",
    [
        {"prompt": ""},
        {"prompt": "Hi", "previous_interaction_id": ""},
    ],
)
async def test_mcp_input_validation(google, arguments):
    async with Client(server.create_server()) as client:
        with pytest.raises(ToolError):
            await client.call_tool("generate_image", arguments)
    google.interactions.create.assert_not_awaited()


def test_instructions_require_reading_prompt_guides():
    instructions = server.create_server().instructions
    assert "REQUIRED" in instructions
    assert "get_prompt_guide" in instructions
