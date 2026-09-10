# Publishing

Nothing in local setup requires a GitHub or Docker Hub account. Local builds and
tests do not push images, create external PRs, or register test servers publicly.

## GitHub / GHCR

1. Create a GitHub repository and push this project. A public repository supports
   the supplied public hosted runners, including `ubuntu-24.04-arm`. For private
   repositories, check runner availability/billing and adjust runners if needed.
2. Enable GitHub Actions. For scheduled draft update PRs, enable **Allow GitHub
   Actions to create and approve pull requests** under repository Actions settings.
3. Require the Docker validation jobs in branch protection before merging releases.
4. Wait for both amd64 and arm64 builds and protocol tests to pass.
5. Push a release tag, for example `v0.1.0`, when ready to publish.

GHCR authentication uses the repository's built-in `GITHUB_TOKEN`; no separate
registry password is needed. CI supplies the real repository URL as the OCI source
label. After first publication, configure the GHCR package visibility as public if
unauthenticated users should be able to pull it.

Tags publish to `ghcr.io/<owner>/<repository>`. Stable versions receive version,
major.minor, and `latest` tags. Use `v0.1.0-rc.1` for a prerelease; `v0.1.0` is a
stable SemVer tag, not a prerelease. Prereleases must not move `latest`.

## Optional Docker Hub

Create a Docker Hub account/repository and configure these GitHub settings:

| Setting | Name | Value |
| --- | --- | --- |
| Repository variable | `DOCKERHUB_IMAGE` | `username/quakeworld-server` |
| Actions secret | `DOCKERHUB_USERNAME` | Docker Hub user |
| Actions secret | `DOCKERHUB_TOKEN` | Access token with push permission |

Without `DOCKERHUB_IMAGE`, the Docker Hub publishing job is skipped. Never put
tokens in `.env`, Dockerfiles, or tracked files.

## Upstream updates

A weekly workflow resolves KTX and qwfwd latest releases to exact commits.
MVDSV follows its development branch (currently `1.20-dev`); its version label is
read from `src/version.h` at the exact selected commit. QTV currently has no
releases, so its default branch is also monitored by commit.
All four are pinned in Dockerfile and their matching source accompanies the image.
An update creates or updates one **draft** PR on `codex/upstream-versions`.
Network/API failures fail the workflow rather than masquerading as releases.

GitHub suppresses new workflow runs for PRs created with `GITHUB_TOKEN`. Run the
**Docker** workflow manually on the proposed branch, review its changes and test
results, then merge it. No update PR auto-merges or publishes an image.

Base image / Actions dependency updates are proposed separately by Dependabot.
To check upstream locally: `./scripts/check-upstream.sh`. `--write` updates pins
in the working tree; inspect the diff before committing.

## Tests before publication

CI builds and runs the nine-service integration suite natively on each target
architecture. It downloads and verifies the original shareware archive locally;
that data is neither part of the image nor uploaded as an artifact. Download
failure fails validation rather than silently skipping the integration tests.

Before the first public release also run `make smoke` with registered game data,
check client play and map rotation, and test public DNS/firewall/NAT from outside
your network. CI verifies protocols and lifecycle, not an entire played match.
Keep PAK files, `.env`, `.secrets`, and `.cache` out of commits.
