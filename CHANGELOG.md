# Changelog

## 0.3.0
- Read-only commands (`greet`, `report`, `list`, `fix`, `diff`, `history`, `raw`, `doctor`) and `pawdit ai` no longer need sudo: the state dir is `2770` for the admin group (`state_group = "auto"` picks `wheel` or `sudo`). Only `pawdit run` needs root. Run `sudo pawdit ai` (or `run`) once to fix permissions of an existing state dir.
- `pawdit fix` without arguments prints a rendered overview of the AI fix for every finding (replaces the interactive menu); `--gen` fills missing texts, `--max N` limits it. `pawdit fix N` still shows the full text.
- Markdown is rendered in the terminal (headings, bold, code, lists, quotes, severity highlights) with `less -R`; plain Markdown when piped or `NO_COLOR` is set.
- More colour in `list`, `diff`, `history` and `doctor`.
- New collectors `docker` (privileged, docker.sock mounts, host namespaces, dangerous caps, unconfined seccomp, sensitive bind mounts, root user, `:latest`, exposed ports, daemon socket/TCP/group/userns) and `docker-images` (Trivy CVEs for running images). Podman is supported for the container checks.

## 0.2.0 — first public release
- Restructured into an installable package (`src/pawdit`), one module per collector, pytest suite, ruff, CI with pinned actions.
- Greeting: summary capped to one sentence and cut on a word boundary; tips are generated per finding (one short call each), so a tip can never be attached to the wrong finding.
- Greeting no longer overflows narrow terminals (width is computed on visible characters).
- Lynis installed from a git clone/tarball now runs from its own directory.
- `install.sh` installs into a venv at `/opt/pawdit` and is idempotent; `--uninstall` added.
- Python 3.10 supported (falls back to `tomli`).

## 0.1.x — internal prototype
