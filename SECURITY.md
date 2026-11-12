# Security

## Reporting
Please use GitHub's private vulnerability reporting ("Security" tab → "Report a vulnerability"). Do not open a public issue for security bugs.

## Design assumptions
- `pawdit run` executes as **root** (it needs to read `/etc/shadow`, run Lynis, AIDE, etc.). It never executes anything produced by the model.
- The LLM only receives normalized findings and returns text. Requests to Ollama carry no `tools`/functions.
- Everything that reaches the terminal (tool output, model output) is stripped of ANSI/OSC escapes, control characters and bidi overrides.
- Findings embedded in prompts are wrapped in `<dados>` and labelled as data; prompt injection through log/file names can at worst produce misleading text, never an action.
- Reports (CVE lists, open ports) live in `/var/lib/pawdit`, mode `2770` root:`state_group` (auto: `wheel` or `sudo`). Read-only commands and `pawdit ai` work without sudo for members of that admin group; only `pawdit run` needs root. Members of that group can already become root, so they are trusted to edit the state.
- Keep `ollama_url` on loopback; a remote URL sends findings off the machine (pawdit warns).
- Pin the version and verify checksums of third-party scanners (e.g. Trivy had a malicious release in March 2026).
