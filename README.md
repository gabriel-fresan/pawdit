# pawdit >:3

**P**aranoid **A**dmin's **W**eekly **D**igest of **I**ssues & **T**hreats

A weekly security audit for your Linux box that orchestrates the tools you already trust (Lynis, ssh-audit, AIDE, chkrootkit, vulnix, Trivy, auditd, Docker/Podman), diffs the result against last week, and has a **small local LLM (<2B, CPU-only, via Ollama) write the summary and fix suggestions**. The short version greets you when you log in over SSH:

```
 /\_/\  pawdit · home-server · 12/11 (hoje)
( °△° ) score 63 (+3) · 0 crit 3 alto 17 méd 119 baixo
 > ^ <  novos 5 (!2 altos) · resolvidos 4
ia ▸ Alto risco por falta de sincronização de tempo e
      SSH com senha habilitada.
  #1 Reiniciar para aplicar o kernel novo
  #2 Desativar login por senha no SSH
pawdit report · list · fix N · diff · history
```

> UI strings and LLM prompts are in Brazilian Portuguese for now. Português: [README.pt-BR.md](README.pt-BR.md).

## How it works

1. A systemd timer (weekly, `Persistent=true`) runs `pawdit run` as root.
2. Collectors run for every tool found in `PATH` and normalize their output into findings (stable id, severity, detail, tool-provided hint). Built-in checks cover failed units, listening ports, UID 0 / empty passwords and `sshd -T`.
3. Findings are diffed against the previous run: **new / persisting / resolved**.
4. The LLM only *writes text* from that list: a one-sentence summary, one short tip per top finding, and a "why / how to fix / caution" text per finding. Facts in the greeting (score, counts) come from code, not from the model. No tools or functions are ever exposed to it.
5. If Ollama is down the report is still produced, with a rule-based summary.

Why a 1–2B model is enough: it does not *audit*, it rewrites facts that were already extracted, with a narrow prompt per finding and schema-constrained JSON for the summary.

## Install

**Debian / Ubuntu**
```bash
sudo apt update && sudo apt install -y lynis aide chkrootkit auditd ssh-audit python3-venv
sudo aideinit -y -f && sudo cp /var/lib/aide/aide.db.new /var/lib/aide/aide.db
curl -fsSL https://ollama.com/install.sh | sh && ollama pull qwen3:1.7b
git clone https://github.com/gabriel-fresan/pawdit && cd pawdit && sudo ./install.sh
pawdit doctor && sudo pawdit run
```
Trivy is not in Ubuntu's repos: install it from the official docs, pinned and checksum-verified.

**NixOS** — import `contrib/nixos/pawdit.nix` and set `services.pawdit.enable = true;` (options: `schedule`, `model`, `manageOllama`, `extraPackages`, `settings`).

**Fedora / Bazzite** — `sudo ./install.sh`. Lynis must be owned by root when run as root: use the distro package or
`sudo git clone https://github.com/CISOfy/lynis /usr/local/lynis && sudo chown -R 0:0 /usr/local/lynis`.

**Greeting on SSH login** — copy `contrib/shell/pawdit.fish` (or `.bash`). It only fires for interactive SSH logins, once per session.

Upgrading is idempotent (`sudo ./install.sh` again); `--uninstall` keeps your config and history.

## Usage

| command | what it does |
|---|---|
| `pawdit` / `greet` | short summary (≤10 lines × 64 cols) |
| `report` | full report with the model's text (uses `bat` if installed) |
| `list [--new] [--min-sev N]` | numbered findings |
| `fix [N\|ID] [--gen]` | recommended fix; no argument opens a compact menu; `--gen` asks the model now |
| `diff` / `history` | what changed / score over time |
| `raw <tool>` | a tool's raw output |
| `sudo run [--no-ai] [--only a,b] [--model M] [--max N]` | audit now |
| `sudo ai [--model M] [--max N]` | regenerate only the AI text (handy to compare models) |
| `doctor` | check tools and Ollama |

State lives in `/var/lib/pawdit` (`0750 root:wheel`): `latest/ → history/<date>/{run.json,findings.json,report.md,raw/}`. AI texts are cached, so persisting findings are not regenerated. Config: `/etc/pawdit.toml` ([example](contrib/pawdit.toml.example)).

## Models

Default `qwen3:1.7b`. Also worth trying: `qwen2.5:1.5b-instruct`, `llama3.2:1b` (fastest), `gemma3:1b`. There is no fine-tuning: quality comes from fixed prompts, constrained output and pre-digested data. Switch with `sudo pawdit ai --model X` and compare.

## Security model

See [SECURITY.md](SECURITY.md). In short: root-run but never executes model output; terminal-escape filtering on everything printed; reports `0640`; keep Ollama on loopback.

## Status

Tested: Lynis 3.1.8 (real report fixture), built-in checks, diff logic, AI plumbing against a fake Ollama (34 tests, CI on Python 3.10/3.12/3.13).
Parsers for AIDE, vulnix, Trivy, ssh-audit and Docker are tested on hand-written samples, not yet on captured real output — fixtures welcome. The NixOS module is syntax-checked only.

## Development

```bash
pip install -e '.[dev]' && ruff check . && pytest -q
```
See [CONTRIBUTING.md](CONTRIBUTING.md). MIT licensed.
