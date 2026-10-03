"""Keep stdout exclusively for the MCP protocol."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from google import genai
from google.genai import errors, types
from google.genai._gaos.lib import compat_errors as interaction_errors
from pydantic import BaseModel, Field

DEFAULT_MODEL = "gemini-3.6-flash"


class InteractionResult(BaseModel):
    """Text and metadata returned by Google's Interactions API."""

    id: str
    status: str
    text: str


def _default_model() -> str:
    return os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL


@asynccontextmanager
async def _google_client() -> AsyncIterator[genai.client.AsyncClient]:
    key = (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
    )
    if not key:
        raise ToolError("Set GEMINI_API_KEY or GOOGLE_API_KEY to use Google AI tools.")

    try:
        # Close both SDK clients, including when a request fails or is cancelled.
        with genai.Client(
            api_key=key,
            vertexai=False,
            enterprise=False,
            http_options=types.HttpOptions(timeout=60_000),
        ) as client:
            async with client.aio as async_client:
                yield async_client
    except interaction_errors.APIConnectionError, httpx.RequestError:
        raise ToolError(
            "Could not reach Google Gen AI. Check your network and try again."
        ) from None
    except interaction_errors.APIError as exc:
        # Interactions currently uses a separate SDK error hierarchy.
        status = f" (HTTP {exc.status_code})" if exc.status_code is not None else ""
        raise ToolError(
            f"Google Interactions request failed{status}. "
            "Check your API key, model access, and quota."
        ) from None
    except errors.APIError as exc:
        # Upstream messages and URLs may contain credentials or submitted content.
        raise ToolError(
            f"Google Gen AI request failed (HTTP {exc.code}). "
            "Check your API key, model access, and quota."
        ) from None


def ping() -> dict[str, str]:
    """Check server health without contacting Google or requiring an API key."""
    return {"status": "ok", "default_model": _default_model()}


async def generate_text(
    prompt: Annotated[str, Field(min_length=1, description="Text to send to Gemini")],
    model: Annotated[str | None, Field(min_length=1)] = None,
    system_instruction: str | None = None,
    max_output_tokens: Annotated[int, Field(ge=1, le=65_536)] = 4096,
    previous_interaction_id: Annotated[str | None, Field(min_length=1)] = None,
    store: bool = False,
) -> InteractionResult:
    """Generate text through Google's Interactions API; may incur charges.

    Uses GEMINI_MODEL (or the server default) unless model is supplied.
    Returns id, status, and text. Set store=True to save this interaction with
    Google for retrieval or continuation using previous_interaction_id.
    """
    if not prompt.strip():
        raise ToolError("prompt must not be blank.")
    selected_model = model.strip() if model is not None else _default_model()
    if not selected_model:
        raise ToolError("model must not be blank.")
    previous_id = (
        previous_interaction_id.strip() if previous_interaction_id is not None else None
    )
    if previous_id == "":
        raise ToolError("previous_interaction_id must not be blank.")

    async with _google_client() as client:
        response = await client.interactions.create(
            model=selected_model,
            input=prompt,
            system_instruction=system_instruction,
            generation_config={"max_output_tokens": max_output_tokens},
            previous_interaction_id=previous_id,
            store=store,
            stream=False,
            background=False,
            timeout=60,
        )

    # Keep status and ID even when output is empty, for example a blocked response.
    return InteractionResult(
        id=response.id or "",
        status=response.status,
        text=response.output_text or "",
    )


async def list_models() -> list[dict[str, str]]:
    """List models available to the configured Google API key."""
    async with _google_client() as client:
        pager = await client.models.list()
        return [
            {
                "name": model.name or "",
                "display_name": model.display_name or "",
                "description": model.description or "",
            }
            async for model in pager
        ]


def create_server() -> FastMCP:
    server = FastMCP(
        "Gemini",
        instructions=(
            "Google Interactions API tools. Google tools require an API key and "
            "may incur charges. Generation returns id, status, and text. Set "
            "store=true to save a turn with Google, then pass its id as "
            "previous_interaction_id to continue. Use list_models to discover models."
        ),
        mask_error_details=True,
    )
    server.tool(ping)
    server.tool(generate_text)
    server.tool(list_models)
    return server


mcp = create_server()


def main() -> None:
    """Run locally over stdin/stdout, without opening a network listener."""
    mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
