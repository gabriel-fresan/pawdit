from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time

_COLOR = False


def set_color(on: bool) -> None:
    global _COLOR
    _COLOR = on


# Remove escapes ANSI/controles e overrides bidi (texto de ferramentas e de LLM vai para o terminal).
_CTRL = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b[@-_]|[\x00-\x08\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]")


def _COLOR_ON():
    return _COLOR


def paint(code, s):
    return f"\x1b[{code}m{s}\x1b[0m" if _COLOR else str(s)


def log(msg):
    print(f"[pawdit {time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def die(msg, code=1):
    print(f"pawdit: {msg}", file=sys.stderr)
    sys.exit(code)


def safe_text(s):
    return _CTRL.sub("", str(s)).replace("\t", " ")


def one_line(s, n=300):
    s = re.sub(r"\s+", " ", safe_text(s)).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def trunc(s, n):
    return s if len(s) <= n else s[: max(0, n - 1)] + "…"


def cut_words(s, n):
    s = one_line(s, 10_000)
    if len(s) <= n:
        return s
    return s[:n].rsplit(" ", 1)[0].rstrip(",;:.") + "…"


def jload(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def jsave(path, obj):
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def sh(cmd, timeout=60, cwd=None):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=timeout, cwd=cwd)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", "não encontrado"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def os_info():
    d = {}
    try:
        with open("/etc/os-release", encoding="utf-8") as fh:
            for line in fh:
                k, _, v = line.strip().partition("=")
                d[k] = v.strip('"')
    except OSError:
        pass
    ident = d.get("ID", "linux")
    if ident == "nixos":
        kind = "declarativo (NixOS)"
    elif os.path.exists("/run/ostree-booted"):
        kind = "imutável (ostree/rpm-ostree)"
    else:
        kind = "tradicional"
    return {"id": ident, "name": d.get("PRETTY_NAME", ident), "kind": kind}


def term_width():
    return shutil.get_terminal_size((80, 24)).columns


def age_days(ts):
    try:
        return (dt.datetime.now() - dt.datetime.fromisoformat(ts)).days
    except (TypeError, ValueError):
        return 0


def page(text, md=False):
    """Print text, rendering Markdown (md=True) and using a pager on a tty."""
    if md:
        from .mdrender import render

        text = render(text)
    if not sys.stdout.isatty():
        print(text)
        return
    lines = text.count("\n") + 1
    if lines < shutil.get_terminal_size((80, 24)).lines - 2:
        print(text)
        return
    pager = shutil.which("less")
    try:
        if pager:
            subprocess.run([pager, "-RFX"], input=text, text=True)
        else:
            print(text)
    except OSError:
        print(text)
