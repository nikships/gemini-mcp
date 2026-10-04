from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from google.genai import errors, interactions, types

from aio_gemini import server


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def google(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    models = SimpleNamespace(generate_content=AsyncMock(), list=AsyncMock())
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


def test_ping_without_credentials():
    assert server.ping() == {
        "status": "ok",
        "default_model": server.DEFAULT_MODEL,
    }


def test_model_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", " custom-model ")
    assert server.ping()["default_model"] == "custom-model"
    monkeypatch.setenv("GEMINI_MODEL", " ")
    assert server.ping()["default_model"] == server.DEFAULT_MODEL


async def test_generate_text_and_cleanup(google):
    result = await server.generate_text("Say hello")
    assert result.model_dump() == {
        "id": "interaction-123",
        "status": "completed",
        "text": "Hello!",
    }
    kwargs = google.interactions.create.call_args.kwargs
    assert kwargs["model"] == server.DEFAULT_MODEL
    assert kwargs["input"] == "Say hello"
    assert kwargs["generation_config"] == {"max_output_tokens": 4096}
    assert kwargs["store"] is False
    assert kwargs["stream"] is False
    assert kwargs["background"] is False
    assert kwargs["timeout"] == 60
    assert kwargs["previous_interaction_id"] is None
    google.models.generate_content.assert_not_awaited()
    assert google.factory.call_args.kwargs["http_options"].timeout == 60_000
    assert google.factory.call_args.kwargs["vertexai"] is False
    assert google.factory.call_args.kwargs["enterprise"] is False
    google.aio.__aexit__.assert_awaited_once()
    google.sync.__exit__.assert_called_once()


async def test_generation_options(google, monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "env-model")
    await server.generate_text("Hello")
    assert google.interactions.create.call_args.kwargs["model"] == "env-model"
    await server.generate_text(
        "Hello",
        model="other-model",
        system_instruction="Be brief",
        max_output_tokens=123,
        previous_interaction_id=" previous-123 ",
        store=True,
    )
    kwargs = google.interactions.create.call_args.kwargs
    assert kwargs["model"] == "other-model"
    assert kwargs["system_instruction"] == "Be brief"
    assert kwargs["generation_config"] == {"max_output_tokens": 123}
    assert kwargs["previous_interaction_id"] == "previous-123"
    assert kwargs["store"] is True


async def test_api_key_precedence_and_fallback(google, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "fallback-key")
    await server.generate_text("Hello")
    assert google.factory.call_args.kwargs["api_key"] == "test-key"
    monkeypatch.setenv("GEMINI_API_KEY", " ")
    await server.generate_text("Hello")
    assert google.factory.call_args.kwargs["api_key"] == "fallback-key"


@pytest.mark.parametrize("tool", [server.generate_text, server.list_models])
async def test_missing_key(tool):
    args = ("Hello",) if tool is server.generate_text else ()
    with pytest.raises(ToolError, match="Set GEMINI_API_KEY or GOOGLE_API_KEY"):
        await tool(*args)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"prompt": " "},
        {"prompt": "Hi", "model": " "},
        {"prompt": "Hi", "previous_interaction_id": " "},
    ],
)
async def test_blank_inputs(google, kwargs):
    with pytest.raises(ToolError, match="must not be blank"):
        await server.generate_text(**kwargs)
    google.factory.assert_not_called()


async def test_no_text_response_preserves_metadata(google):
    google.interactions.create.return_value = interactions.Interaction(
        id="empty-interaction", status="completed"
    )
    result = await server.generate_text("Hello")
    assert result.model_dump() == {
        "id": "empty-interaction",
        "status": "completed",
        "text": "",
    }


async def test_incomplete_response_status(google):
    google.interactions.create.return_value = interactions.Interaction(
        id="partial-interaction", status="incomplete"
    )
    assert (await server.generate_text("Hello")).status == "incomplete"


@pytest.mark.parametrize("operation", ["create", "list"])
async def test_api_errors_are_redacted(google, operation):
    if operation == "create":
        google.interactions.create.side_effect = (
            server.interaction_errors.APIStatusError(
                "sensitive-upstream-detail",
                response=httpx.Response(
                    429,
                    request=httpx.Request("POST", "https://example.test/interactions"),
                ),
                body={"sensitive": "upstream-detail"},
            )
        )
    else:
        google.models.list.side_effect = errors.APIError(
            429, {"error": {"message": "sensitive-upstream-detail", "status": "ERROR"}}
        )
    with pytest.raises(ToolError, match="HTTP 429") as exc:
        if operation == "create":
            await server.generate_text("Hello")
        else:
            await server.list_models()
    assert "sensitive-upstream-detail" not in str(exc.value)
    assert exc.value.__suppress_context__
    google.aio.__aexit__.assert_awaited_once()
    google.sync.__exit__.assert_called_once()


async def test_network_error_is_redacted(google):
    google.interactions.create.side_effect = httpx.ConnectError("sensitive-request-url")
    with pytest.raises(ToolError, match="Could not reach") as exc:
        await server.generate_text("Hello")
    assert "sensitive-request-url" not in str(exc.value)


async def test_list_models(google):
    async def models() -> AsyncIterator[types.Model]:
        yield types.Model(name="models/example", display_name="Example")
        yield types.Model(name="models/other", description="Other model")

    google.models.list.return_value = models()
    assert await server.list_models() == [
        {"name": "models/example", "display_name": "Example", "description": ""},
        {"name": "models/other", "display_name": "", "description": "Other model"},
    ]


async def test_mcp_discovery_and_generation(google):
    async with Client(server.create_server()) as client:
        tools = await client.list_tools()
        assert {"ping", "generate_text", "list_models"} <= {tool.name for tool in tools}
        result = await client.call_tool("generate_text", {"prompt": "Hi"})
        assert result.structured_content == {
            "id": "interaction-123",
            "status": "completed",
            "text": "Hello!",
        }
        await client.call_tool(
            "generate_text",
            {
                "prompt": "Continue",
                "previous_interaction_id": result.data.id,
                "store": True,
            },
        )
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
        await server.generate_text("Hello")
    assert "sensitive-upstream-detail" not in str(exc.value)
    assert exc.value.__suppress_context__
    google.aio.__aexit__.assert_awaited_once()
    google.sync.__exit__.assert_called_once()


@pytest.mark.parametrize(
    "arguments",
    [
        {"prompt": ""},
        {"prompt": "Hi", "max_output_tokens": 0},
        {"prompt": "Hi", "max_output_tokens": 65_537},
        {"prompt": "Hi", "model": ""},
        {"prompt": "Hi", "previous_interaction_id": ""},
    ],
)
async def test_mcp_input_validation(google, arguments):
    async with Client(server.create_server()) as client:
        with pytest.raises(ToolError):
            await client.call_tool("generate_text", arguments)
    google.interactions.create.assert_not_awaited()
