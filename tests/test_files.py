import asyncio
from pathlib import Path

import httpx
import pytest
from fastmcp.exceptions import ToolError

from gemini_mcp import server


def file_info(name="files/generated", state="ACTIVE", generated=True):
    return {
        "name": name,
        "mimeType": "video/mp4",
        "state": state,
        "uri": f"https://generativelanguage.googleapis.com/v1beta/{name}",
        "downloadUri": f"https://generativelanguage.googleapis.com/v1beta/{name}:download"
        if generated
        else None,
        "sizeBytes": "5",
        "expirationTime": "2026-10-05T00:00:00Z",
    }


async def test_file_get_list_delete_real_sdk(sdk_transport):
    requests = []

    def handle(request):
        requests.append(request)
        if request.method == "DELETE":
            return httpx.Response(200, json={})
        if request.url.path.endswith("/files"):
            return httpx.Response(
                200,
                json={
                    "files": [
                        file_info("files/first"),
                        file_info("files/second"),
                    ]
                },
            )
        return httpx.Response(200, json=file_info())

    sdk_transport(handle)
    result = await server.get_file("files/generated")
    assert result.state == "ACTIVE"
    assert result.mime_type == "video/mp4"
    assert result.size_bytes == 5
    assert result.expiration_time == "2026-10-05T00:00:00+00:00"
    assert len(await server.list_files(limit=1)) == 1
    assert await server.delete_file("files/generated") == {
        "name": "files/generated",
        "status": "deleted",
    }
    assert len(requests) == 3
    assert requests[-1].method == "DELETE"


async def test_real_sdk_upload_returns_processing(sdk_transport, tmp_path):
    path = tmp_path / "video.mp4"
    path.write_bytes(b"video")
    requests = []

    def handle(request):
        requests.append(request)
        if "upload" in request.url.path:
            return httpx.Response(
                200,
                headers={
                    "x-goog-upload-url": "https://generativelanguage.googleapis.com/resumable",
                },
            )
        assert request.url.path == "/resumable"
        assert request.content == b"video"
        return httpx.Response(
            200,
            headers={"x-goog-upload-status": "final"},
            json={
                "file": file_info(
                    "files/uploaded", state="PROCESSING", generated=False
                ),
            },
        )

    sdk_transport(handle)
    result = await server.upload_file(str(path), "video/mp4", display_name="A video")
    assert result.name == "files/uploaded"
    assert result.state == "PROCESSING"
    assert len(requests) == 2


async def test_generated_download_streams_to_private_file(sdk_transport, tmp_path):
    requests = []

    def handle(request):
        requests.append(request)
        if request.url.path.endswith(":download"):
            return httpx.Response(200, content=b"video")
        return httpx.Response(200, json=file_info())

    sdk_transport(handle)
    first = await server.download_file(
        "files/generated", output_directory=str(tmp_path)
    )
    second = await server.download_file(
        "files/generated", output_directory=str(tmp_path)
    )
    assert first["path"] != second["path"]
    assert await asyncio.to_thread(Path(first["path"]).read_bytes) == b"video"
    assert Path(first["path"]).suffix == ".mp4"
    assert all(r.url.host == "generativelanguage.googleapis.com" for r in requests)


@pytest.mark.parametrize(
    "state, generated",
    [
        ("PROCESSING", True),
        ("FAILED", True),
        ("ACTIVE", False),
    ],
)
async def test_cannot_download_unready_or_uploaded_files(
    sdk_transport, state, generated
):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=file_info(state=state, generated=generated))

    sdk_transport(handle)
    with pytest.raises(ToolError):
        await server.download_file("files/generated")
    assert len(requests) == 1


async def test_failed_download_removes_partial_file_and_redacts_error(
    sdk_transport,
    tmp_path,
):
    def handle(request):
        if request.url.path.endswith(":download"):
            return httpx.Response(
                403,
                json={
                    "error": {
                        "code": 403,
                        "message": "sensitive-google-detail",
                    }
                },
            )
        return httpx.Response(200, json=file_info())

    sdk_transport(handle)
    with pytest.raises(ToolError, match="HTTP 403") as exc:
        await server.download_file("files/generated", output_directory=str(tmp_path))
    assert "sensitive-google-detail" not in str(exc.value)
    assert list(tmp_path.iterdir()) == []


async def test_upload_missing_file_never_calls_api(sdk_transport, tmp_path):
    def handle(request):
        pytest.fail("Unexpected API request")

    sdk_transport(handle)
    with pytest.raises(ToolError, match="regular file"):
        await server.upload_file(str(tmp_path / "missing.mp4"), "video/mp4")
