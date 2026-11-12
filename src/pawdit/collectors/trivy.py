from __future__ import annotations

import json
import shutil

from ..models import SEV, F
from ..util import one_line, sh

_TRIVY_SEV = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def parse_trivy(txt, top=15):
    try:
        data = json.loads(txt)
    except ValueError:
        return []
    pk = {}
    for res in data.get("Results") or []:
        for v in res.get("Vulnerabilities") or []:
            pk.setdefault(v.get("PkgName", "?"), []).append(v)
    rows = []
    for name, vs in pk.items():
        sev = max(_TRIVY_SEV.get(v.get("Severity", ""), 0) for v in vs)
        rows.append((sev, len(vs), name, vs))
    rows.sort(key=lambda r: (-r[0], -r[1]))
    fs = []
    for sev, n, name, vs in rows[:top]:
        fixed = next((v.get("FixedVersion") for v in vs if v.get("FixedVersion")), "")
        fs.append(
            F(
                "trivy",
                f"PKG-{name}",
                f"{name}: {n} CVEs corrigíveis (máx {SEV.get(sev, '?')})",
                sev,
                ", ".join(sorted({v.get("VulnerabilityID", "?") for v in vs})[:6]),
                f"atualize {name}" + (f" para {fixed}" if fixed else ""),
            )
        )
    if len(rows) > top:
        fs.append(
            F(
                "trivy",
                "PKG-OUTROS",
                f"+{len(rows) - top} pacotes com CVEs de menor severidade",
                1,
                ", ".join(r[2] for r in rows[top : top + 8]),
            )
        )
    return fs


def collect(cfg, ctx):
    exe = shutil.which("trivy")
    if not exe or ctx.os["id"] == "nixos":
        return None
    cmd = [exe, "rootfs", "--quiet", "--format", "json", "--pkg-types", "os", "--scanners", "vuln", "--ignore-unfixed"]
    for d in ("/proc", "/sys", "/dev", "/run", "/sysroot", "/ostree", "/var/lib/containers"):
        cmd += ["--skip-dirs", d]
    rc, out, err = sh(cmd + ["/"], cfg["tool_timeout"])
    if rc != 0:
        raise RuntimeError(one_line(err, 200) or f"trivy rc={rc}")
    return parse_trivy(out), {}, out
