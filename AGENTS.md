# AGENTS.md

## Releases

The package is published to PyPI as `aio-gemini-mcp`. Users run it with
`uvx aio-gemini-mcp@latest`, so unreleased changes never reach them.

**"Push" means ship it to everyone, not just to GitHub.** When the user says
"push" (or "commit and push", "push it", etc.), they want the change fixed for
every user of the package. A push alone does nothing for users, so always do the
whole flow below, including the bump and the GitHub release, without being asked
and without handing any step back to the user. Never stop after `git push`.

**Every push to `main` must bump the version.** Before pushing:

1. Bump `version` in `pyproject.toml` (patch for fixes and tweaks, minor for new
   tools or behavior changes).
2. Run `uv lock` so `uv.lock` matches.
3. Commit and push.
4. Create a GitHub release for the new version. Publishing the release runs
   `.github/workflows/publish.yml`, which uploads to PyPI via trusted publishing.
5. Confirm the publish workflow succeeded (`gh run list --workflow publish.yml`).

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
