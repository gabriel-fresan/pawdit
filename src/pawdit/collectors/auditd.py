from __future__ import annotations

import re
import shutil

from ..models import F
from ..util import one_line, sh


def collect(cfg, ctx):
    exe = shutil.which("aureport")
    if not exe:
        return None
    rc, out, err = sh([exe, "--auth", "--failed", "--summary", "--start", "week-ago", "-i"], 60)
    if rc != 0:
        return None
    total = sum(int(m.group(1)) for m in re.finditer(r"^\s*(\d+)\s+\S+", out, re.M))
    fs = []
    if total >= 5:
        fs.append(
            F(
                "auditd",
                "AUDIT-AUTHFAIL",
                f"{total} falhas de autenticação na última semana (auditd)",
                2 if total >= 20 else 1,
                one_line(out, 200),
                "veja 'aureport --auth --failed -i' e considere fail2ban / limitar SSH por chave",
            )
        )
    return fs, {}, out
