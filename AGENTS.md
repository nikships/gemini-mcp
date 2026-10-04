# AGENTS.md

## Releases

The package is published to PyPI as `aio-gemini-mcp`. Users run it with
`uvx aio-gemini-mcp@latest`, so unreleased changes never reach them.

**Every push to `main` must bump the version.** Before pushing:

1. Bump `version` in `pyproject.toml` (patch for fixes and tweaks, minor for new
   tools or behavior changes).
2. Run `uv lock` so `uv.lock` matches.
3. Commit and push.
4. Create a GitHub release for the new version. Publishing the release runs
   `.github/workflows/publish.yml`, which uploads to PyPI via trusted publishing.

```sh
gh release create vX.Y.Z --title vX.Y.Z --generate-notes
```

PyPI rejects re-uploads of an existing version, so a push without a bump cannot
be published.

## Validate

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
```
