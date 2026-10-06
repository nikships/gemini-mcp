import httpx
import pytest
from google import genai

from aio_gemini import server


@pytest.fixture(autouse=True)
def media_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_OUTPUT_DIR", str(tmp_path / "outputs"))


@pytest.fixture
def sdk_transport(monkeypatch):
    """Run the actual SDK with all network requests intercepted locally."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    real_client = genai.Client

    def install(handler):
        def factory(**kwargs):
            kwargs["http_options"].httpx_async_client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler)
            )
            return real_client(**kwargs)

        monkeypatch.setattr(server.genai, "Client", factory)

    return install
