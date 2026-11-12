from __future__ import annotations

import hashlib

from .util import one_line

SEV = {4: "crítico", 3: "alto", 2: "médio", 1: "baixo", 0: "info"}


SEV_COLOR = {4: "1;35", 3: "31", 2: "33", 1: "34", 0: "2"}


def F(tool, id_, title, sev, detail="", hint="", kx=""):
    id_ = one_line(id_, 80)
    key = hashlib.sha1(f"{tool}|{id_}|{kx}".encode()).hexdigest()[:10]
    return {
        "key": key,
        "tool": tool,
        "id": id_,
        "sev": sev,
        "title": one_line(title, 160),
        "detail": one_line(detail, 400),
        "hint": one_line(hint, 300),
    }
