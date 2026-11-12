from __future__ import annotations

import re
import shutil

from ..models import F
from ..util import sh


def collect(cfg, ctx):
    exe = shutil.which("chkrootkit")
    if not exe:
        return None
    rc, out, err = sh([exe, "-q"], cfg["tool_timeout"])
    fs = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        bad = "INFECTED" in line.upper() and "NOT INFECTED" not in line.upper()
        slug = re.sub(r"\W+", "-", line.lower())[:40]
        fs.append(
            F(
                "chkrootkit",
                f"CHK-{slug}",
                line,
                3 if bad else 1,
                "",
                "chkrootkit gera falsos positivos: confirme com verificação de pacotes (rpm -V / debsums) antes de agir",
            )
        )
    return fs, {}, out
