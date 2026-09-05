# Security policy

Please report vulnerabilities privately through GitHub's private vulnerability
reporting feature once the repository is published. Do not open a public issue
for credentials, exploitable server details, or unpublished vulnerabilities.

Operational recommendations:

- expose only the selected UDP game port
- keep RCON in a Docker secret and rotate it after accidental disclosure
- retain the read-only filesystem, dropped capabilities, and non-root user
- keep Docker, the host kernel, MVDSV, and KTX patched
- back up configuration, logs, demos, maps, and licensed game data separately
