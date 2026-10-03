# Gemini MCP server

A Python FastMCP server using **stdio**, the official **Google Gen AI SDK**, and
the **Google Interactions API** for generation, not `models.generate_content`.
No HTTP server or listening port is started. Stdout is reserved for MCP messages;
diagnostics go to stderr.

## Setup

This machine already has uv and Python installed. For a fresh checkout:

```sh
cd /home/factory-user/gemini-mcp
uv sync --frozen
```

uv installs the Python version in `.python-version` if needed. `uv.lock` pins all
dependencies for reproducible installs. Stable versions selected at setup:

| Component | Version |
| --- | --- |
| uv | 0.12.22 |
| Python | 3.14.8 |
| FastMCP | 4.0.10 |
| google-genai | 2.28.0 |

uv is installed in `/home/factory-user/.local/bin`. Open a new terminal to pick up
the updated PATH, or use that absolute path.

## Run

Supply your Gemini Developer API key through the MCP client's environment.
`GEMINI_API_KEY` takes precedence over `GOOGLE_API_KEY`. No key is stored in this
project. `.env` files are **not** automatically loaded.

```sh
uv --directory /home/factory-user/gemini-mcp run --frozen gemini-mcp
```

Also supported: `uv run python -m gemini_mcp` from the project directory.
The server waits for MCP messages on stdin; it is not an interactive terminal app.
An MCP client should launch it as a subprocess.

Copy the `gemini` entry from `mcp-config.example.json` into your client's
`mcpServers` configuration. Replace the example key locally or use your client's
secret/environment mechanism. Do not commit credentials. Adapt the absolute
paths if you move the project. Client configuration formats can vary.

## Tools

| Tool | Purpose |
| --- | --- |
| `ping` | Local health check and current default model; no API key needed |
| `generate_text` | Create a Gemini interaction and return its ID, status, and text |
| `list_models` | List models available to your Google API key |

`generate_text` calls `client.aio.interactions.create`. It accepts `prompt`,
optional `model`, optional `system_instruction`, `max_output_tokens` (default
4096, allowed range 1–65536), optional `previous_interaction_id`, and `store`
(default `false`). Model-specific
limits still apply. Set `GEMINI_MODEL` to change the default, `gemini-3.6-flash`,
or pass `model` per request. Use `list_models` to check your account's access.

Generation now returns a structured object, not the old bare text string:

```json
{"id": "interaction-id", "status": "completed", "text": "Hello!"}
```

To continue a conversation, call `generate_text` with `store: true`, then pass
the returned `id` as `previous_interaction_id` on your next call. Keep
`store: true` on each turn you want to continue later. Storage is opt-in:
`store: false` requests that Google not save this interaction for later
retrieval or continuation; it does not bypass Google's other data policies.
System instructions and generation options are supplied on each call.

Requests are non-streaming and foreground-only. The returned status is preserved
even if text is empty, rather than reporting an incomplete or blocked response
as successful text. `list_models` still uses the SDK's model-discovery endpoint.

Google requests use asynchronous I/O and a 60-second request timeout. Clients
are closed after each tool call. Upstream error details are redacted from tool
errors. Prompts are sent to Google and API use may incur charges. Missing keys
do not prevent startup, tool discovery, or health checks.

## Develop and validate

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv build
```

Tests mock Google requests, verify the real SDK's Interactions HTTP transport,
and exercise real stdio subprocesses with both current and legacy MCP clients.
They need no credentials and make no Google
API calls. Live generation requires your own API key and is not covered by
these tests.

To upgrade to newer stable dependencies intentionally:

```sh
uv lock --upgrade
uv sync --frozen
uv run pytest
```
