from __future__ import annotations

import re
import shutil

from ..models import F
from ..util import one_line, sh


def parse_aide(txt):
    counts = {}
    for k in ("Added", "Removed", "Changed"):
        m = re.search(rf"{k} entries:\s+(\d+)", txt)
        counts[k] = int(m.group(1)) if m else 0
    paths_, sec = {"Added": [], "Removed": [], "Changed": []}, None
    for line in txt.splitlines():
        h = re.match(r"^(Added|Removed|Changed) entries:\s*$", line.strip())
        if h:
            sec = h.group(1)
            continue
        if line.startswith("Detailed information"):
            sec = None
        m = re.match(r"^[^:\s][^:]*:\s+(/.+)$", line)
        if sec and m and m.group(1) not in paths_[sec]:
            paths_[sec].append(m.group(1))
    fs = []
    names = {"Added": ("adicionados", 2), "Removed": ("removidos", 2), "Changed": ("alterados", 3)}
    for k, n in counts.items():
        if n:
            lab, sev = names[k]
            fs.append(
                F(
                    "aide",
                    f"AIDE-{k.upper()}",
                    f"AIDE: {n} arquivos {lab} desde a baseline",
                    sev,
                    ", ".join(paths_[k][:8]),
                    "se a mudança é legítima (update/config), rode 'aide --update' e promova o novo banco",
                )
            )
    return fs


def collect(cfg, ctx):
    exe = shutil.which("aide")
    if not exe:
        return None
    rc, out, err = sh([exe, "--check"], cfg["tool_timeout"])
    txt = out + err
    if rc >= 14 or re.search(r"couldn.t open file|no such file", txt, re.I):
        return (
            [
                F(
                    "aide",
                    "AIDE-NOBASELINE",
                    "AIDE instalado, mas sem baseline/config válida",
                    1,
                    one_line(txt, 200),
                    "crie a baseline com 'aide --init' (e mova o .new para o caminho do banco)",
                )
            ],
            {},
            txt,
        )
    return parse_aide(txt), {}, txt
