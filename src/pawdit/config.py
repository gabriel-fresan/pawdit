from __future__ import annotations

import os

from .util import log

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None


DEFAULTS = {
    "state_dir": "/var/lib/pawdit",
    "state_group": "auto",  # grupo que lê/escreve o estado: auto = wheel ou sudo (o que existir)
    "ollama_url": "http://127.0.0.1:11434",
    "model": "qwen3:1.7b",
    "ai_timeout": 900,  # segundos por chamada (CPU é lenta)
    "max_ai_findings": 12,  # quantos achados recebem texto de solução no run semanal
    "tool_timeout": 1800,
    "history_keep": 26,
    "stale_days": 10,
    "greet_width": 64,
    "expected_ports": [22],  # portas esperadas abertas p/ a rede (builtin)
    "ssh_audit_target": "127.0.0.1:22",
    "tools": ["builtin", "lynis", "ssh-audit", "aide", "chkrootkit", "vulnix", "trivy", "auditd"],
}


def load_cfg():
    cfg = dict(DEFAULTS)
    path = os.environ.get("PAWDIT_CONFIG", "/etc/pawdit.toml")
    if os.path.exists(path):
        try:
            if tomllib is None:
                raise RuntimeError("Python < 3.11: instale o pacote tomli para ler o TOML")

            with open(path, "rb") as fh:
                cfg.update(tomllib.load(fh))
        except Exception as e:  # noqa: BLE001
            log(f"config ignorada ({path}): {e}")
    for env, key in (("PAWDIT_STATE", "state_dir"), ("PAWDIT_MODEL", "model"), ("PAWDIT_OLLAMA_URL", "ollama_url")):
        if os.environ.get(env):
            cfg[key] = os.environ[env]
    return cfg


def paths(cfg):
    s = cfg["state_dir"]
    return {
        "state": s,
        "hist": os.path.join(s, "history"),
        "latest": os.path.join(s, "latest"),
        "cache": os.path.join(s, "aicache.json"),
        "lock": os.path.join(s, ".lock"),
    }


def resolve_group(cfg):
    """Group allowed to read (and regenerate AI text in) the state dir. ``auto`` picks wheel or sudo."""
    want = cfg.get("state_group")
    if want and want != "auto":
        return want
    try:
        import grp
    except ImportError:
        return None
    for name in ("wheel", "sudo"):
        try:
            grp.getgrnam(name)
            return name
        except KeyError:
            continue
    return None
