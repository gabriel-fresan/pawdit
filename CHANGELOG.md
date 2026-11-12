# Changelog

## 0.2.0 — first public release
- Restructured into an installable package (`src/pawdit`), one module per collector, pytest suite, ruff, CI with pinned actions.
- Greeting: summary capped to one sentence and cut on a word boundary; tips are generated per finding (one short call each), so a tip can never be attached to the wrong finding.
- Greeting no longer overflows narrow terminals (width is computed on visible characters).
- Lynis installed from a git clone/tarball now runs from its own directory.
- `install.sh` installs into a venv at `/opt/pawdit` and is idempotent; `--uninstall` added.
- Python 3.10 supported (falls back to `tomli`).

## 0.1.x — internal prototype
