from __future__ import annotations

import json
import shutil

from ..models import F
from ..util import one_line, sh


def parse_vulnix(txt, top=15):
    try:
        data = json.loads(txt)
    except ValueError:
        return []
    rows = []
    for it in data if isinstance(data, list) else []:
        cves = [c for c in it.get("affected_by", []) if c not in it.get("whitelisted", [])]
        if not cves:
            continue
        scores = [v for v in (it.get("cvssv3_basescore") or {}).values() if isinstance(v, (int, float))]
        rows.append((max(scores) if scores else 0, it.get("pname") or it.get("name", "?"), it.get("name", "?"), cves))
    rows.sort(key=lambda r: (-r[0], -len(r[3])))
    fs = []
    for score, pname, name, cves in rows[:top]:
        sev = 4 if score >= 9 else 3 if score >= 7 else 2 if score >= 4 else 1
        fs.append(
            F(
                "vulnix",
                f"NIX-{pname}",
                f"{name}: {len(cves)} CVEs (CVSS máx {score})",
                sev,
                ", ".join(sorted(cves)[:6]),
                "atualize o canal/flake e reconstrua (nix flake update; nixos-rebuild switch); vulnix casa por nome, valide falsos positivos",
            )
        )
    rest = rows[top:]
    if rest:
        fs.append(
            F(
                "vulnix",
                "NIX-OUTROS",
                f"+{len(rest)} pacotes do closure com CVEs de menor severidade",
                1,
                ", ".join(r[1] for r in rest[:8]),
            )
        )
    return fs


def collect(cfg, ctx):
    exe = shutil.which("vulnix")
    if not exe or ctx.os["id"] != "nixos":
        return None
    rc, out, err = sh([exe, "--system", "--json"], cfg["tool_timeout"])  # rc 2 = achou CVEs
    if rc not in (0, 2):
        raise RuntimeError(one_line(err, 200) or f"vulnix rc={rc}")
    return parse_vulnix(out), {}, out
