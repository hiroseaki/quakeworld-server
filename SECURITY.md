# Security

Use GitHub private vulnerability reporting once the repository is published.
Do not include credentials or exploitable server details in public issues.

The supplied services run as UID/GID 10001 with a read-only root filesystem,
private runtime tmpfs, dropped capabilities, no-new-privileges, and resource limits.
Expose only selected UDP game/proxy ports and the TCP QTV port. Game QTV source
ports stay inside the Compose network by default.

Use distinct RCON, KTX admin, upstream QTV and viewer passwords as appropriate.
Environment values are convenient but visible to Docker administrators; optional
password files require correct host permissions. Runtime configs are private, not
image layers. Keep `.env`, `.secrets`, PAK files, and `.cache` out of Git.

MVDSV retains authenticated RCON by default. Use a compatible client; sending a
plain password to authenticated RCON can cause upstream to log the failed request.
Trusted custom configuration can change security settings and execute console
commands; only mount files controlled by the operator.

qwfwd is a public forwarding proxy when exposed: choose its host/network placement
and firewall policy deliberately. Health checks prove that a process responds;
they do not imply every remote stream or route is available. QTV HTTP upload and
asset downloads are disabled by default.

Docker console logs rotate; demo limits invoke MVDSV cleanup. Back up wanted
recordings and persistent volumes. Keep Docker, the host and upstream components
patched; review update PRs before publishing a new image.
