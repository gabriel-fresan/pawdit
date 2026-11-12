from __future__ import annotations

import re
import shutil

from ..models import F
from ..util import sh

_SSHA = re.compile(r"^\((\w+)\)\s+(\S+)\s+--\s+\[(fail|warn)\]\s*(.*)$")


def parse_ssh_audit(out):
    groups = {"fail": [], "warn": []}
    removes = []
    for line in out.splitlines():
        m = _SSHA.match(line.strip())
        if m:
            groups[m.group(3)].append(f"{m.group(2)} ({m.group(1)})")
            continue
        m = re.match(r"^\(rec\)\s+-(\S+)", line.strip())
        if m:
            removes.append(m.group(1))
    fs = []
    for lvl, sev, label in (("fail", 3, "reprovados"), ("warn", 2, "com aviso")):
        items = groups[lvl]
        if items:
            hint = ("remova no sshd_config: " + ", ".join(removes[:6])) if lvl == "fail" and removes else ""
            fs.append(
                F(
                    "ssh-audit",
                    f"SSH-{lvl.upper()}",
                    f"SSH: {len(items)} algoritmos {label} (ssh-audit)",
                    sev,
                    ", ".join(items[:8]),
                    hint,
                )
            )
    return fs


def collect(cfg, ctx):
    exe = shutil.which("ssh-audit")
    if not exe:
        return None
    host, _, port = cfg["ssh_audit_target"].rpartition(":")
    rc, out, err = sh([exe, "-n", "-p", port or "22", host or "127.0.0.1"], 120)
    if "[fail]" not in out and "[warn]" not in out and "(gen)" not in out:
        return None  # sshd não está respondendo nesse alvo
    return parse_ssh_audit(out), {}, out
