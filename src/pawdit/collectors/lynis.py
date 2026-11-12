from __future__ import annotations

import os
import shutil

from ..models import F
from ..util import one_line, sh

HIGH_PREFIX = {"SSH", "FIRE", "AUTH", "NETW"}


def parse_lynis(text):
    fs, meta = [], {}
    for line in text.splitlines():
        if line.startswith(("warning[]=", "suggestion[]=")):
            kind, _, val = line.partition("[]=")
            p = (val.split("|") + [""] * 4)[:4]
            id_, desc, det, sol = p
            det = "" if det.strip() in ("-", "") else det
            sol = "" if sol.strip() in ("-", "") else sol
            sev = 3 if kind == "warning" else (2 if id_.split("-")[0] in HIGH_PREFIX else 1)
            fs.append(F("lynis", id_, desc, sev, det, sol, kx=desc))
        elif line.startswith("hardening_index="):
            try:
                meta["score"] = int(line.split("=", 1)[1])
            except ValueError:
                pass
    return fs, meta


def collect(cfg, ctx):
    exe = shutil.which("lynis")
    if not exe:
        return None
    os.makedirs(ctx.tmp, exist_ok=True)
    rep, logf = os.path.join(ctx.tmp, "lynis-report.dat"), os.path.join(ctx.tmp, "lynis.log")
    home = os.path.dirname(os.path.realpath(exe))
    cwd = home if os.path.isdir(os.path.join(home, "include")) else None  # instalação via git clone/tarball
    rc, out, err = sh(
        [exe, "audit", "system", "--cronjob", "--no-colors", "--quiet", "--logfile", logf, "--report-file", rep],
        cfg["tool_timeout"],
        cwd=cwd,
    )
    if not os.path.exists(rep):
        raise RuntimeError(
            "lynis não gerou o report: "
            + (one_line(out + err, 160) or f"rc={rc}")
            + " (arquivos do lynis precisam pertencer a root)"
        )
    with open(rep, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    fs, meta = parse_lynis(text)
    return fs, meta, text
