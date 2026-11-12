# Contributing

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
ruff check . && ruff format --check . && pytest -q
```

## Adding a collector
1. Create `src/pawdit/collectors/<tool>.py` with a pure `parse_<tool>(text) -> list[finding]` and a `collect(cfg, ctx)` returning `(findings, meta, raw_text)`, or `None` if the tool is not installed.
2. Build findings with `pawdit.models.F(tool, id, title, severity, detail, hint)`. Keep ids stable across runs (they drive the new/resolved diff); put volatile numbers in the title, not the id.
3. Register it in `collectors/__init__.py` and add a parser test with a **real** sample of the tool's output in `tests/fixtures/`.

Severity scale: 4 critical · 3 high · 2 medium · 1 low · 0 info.

## Rules of thumb
- Collectors never modify the system (no `--remediate`, no `aide --update`).
- Anything printed to a terminal goes through `util.safe_text`.
- Keep the greeting within 10 lines × 64 columns.
