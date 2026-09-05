# Publishing images

## GitHub Container Registry

The `docker.yml` workflow publishes `v*` tags to:

```text
ghcr.io/<github-owner>/<repository>:<version>
```

Create a GitHub repository, push this project, then create a semantic version
tag such as `v0.1.0`. The workflow uses the built-in `GITHUB_TOKEN` for GHCR.

## Docker Hub

In the GitHub repository settings, add:

- variable `DOCKERHUB_IMAGE`, for example `username/quakeworld-server`
- secret `DOCKERHUB_USERNAME`
- secret `DOCKERHUB_TOKEN` (an access token, not your account password)

The Docker Hub job is skipped when `DOCKERHUB_IMAGE` is unset.

Before the first public release, replace the placeholder source URL in the
Dockerfile or keep passing `SOURCE_URL` from CI as the workflow does.

## Release checklist

1. Run `make check` and `make smoke` with a legal local `pak0.pak`.
2. Review upstream MVDSV/KTX release notes and update both version labels and
   pinned commits together.
3. Build both target architectures in CI.
4. Confirm the image starts as UID/GID 10001 and becomes healthy.
5. Tag a pre-release (`v0.1.0`) before advertising `latest`.
