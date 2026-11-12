from __future__ import annotations

import os
import re
import shutil

from ..models import F
from ..util import sh


def collect(cfg, ctx):
    fs, raw = [], []

    def add(*a, **k):
        fs.append(F("builtin", *a, **k))

    rc, out, _ = sh(["systemctl", "--failed", "--no-legend", "--plain"], 30)
    raw.append("# systemctl --failed\n" + out)
    for line in out.splitlines():
        u = (line.split() or [""])[0]
        if u:
            add(f"UNIT-{u}", f"unit systemd falhou: {u}", 2, line, f"veja: journalctl -u {u} -b --no-pager | tail -50")

    if os.path.exists("/var/run/reboot-required"):
        add("REBOOT", "reinício pendente (atualização de kernel/libs)", 1, "", "reinicie quando possível")
    cur, boot = "/run/current-system/kernel", "/run/booted-system/kernel"
    if os.path.islink(cur) and os.path.islink(boot) and os.path.realpath(cur) != os.path.realpath(boot):
        add(
            "REBOOT",
            "kernel novo instalado; reinício pendente",
            1,
            "",
            "reinicie para ativar o kernel da geração atual",
        )

    expected = {str(p) for p in cfg["expected_ports"]}
    rc, out, _ = sh(["ss", "-H", "-ltnup"], 30)
    raw.append("# ss -ltnup\n" + out)
    seen = set()
    for line in out.splitlines():
        f = line.split()
        if len(f) < 6:
            continue
        proto, local = f[0], f[4]
        host, _, port = local.rpartition(":")
        if host.strip("[]").startswith(("127.", "::1")) or port in expected or (proto, port) in seen:
            continue
        seen.add((proto, port))
        m = re.search(r'\("([^"]+)"', line)
        add(
            f"PORT-{proto}/{port}",
            f"porta {port}/{proto} aberta para a rede ({m.group(1) if m else '?'})",
            1,
            local,
            "se for esperado, inclua em expected_ports no /etc/pawdit.toml; senão feche no serviço/firewall",
        )

    try:
        with open("/etc/passwd", encoding="utf-8") as fh:
            for line in fh:
                p = line.split(":")
                if len(p) > 3 and p[2] == "0" and p[0] != "root":
                    add(
                        f"UID0-{p[0]}",
                        f"conta '{p[0]}' tem UID 0",
                        4,
                        "",
                        "revise /etc/passwd; remova a conta ou troque o UID",
                    )
        with open("/etc/shadow", encoding="utf-8") as fh:
            for line in fh:
                p = line.split(":")
                if len(p) > 1 and p[1] == "":
                    add(
                        f"NOPASS-{p[0]}",
                        f"conta '{p[0]}' sem senha",
                        4,
                        "",
                        "defina senha ou bloqueie: passwd -l " + p[0],
                    )
    except OSError:
        pass

    sshd = shutil.which("sshd") or "/usr/sbin/sshd"
    rc, out, _ = sh([sshd, "-T"], 20)
    if rc == 0:
        cf = {}
        for line in out.splitlines():
            k, _, v = line.partition(" ")
            cf.setdefault(k, v.strip())
        raw.append(
            "# sshd -T (seleção)\n"
            + "\n".join(
                f"{k} {cf.get(k, '?')}" for k in ("permitrootlogin", "passwordauthentication", "permitemptypasswords")
            )
        )
        if cf.get("permitemptypasswords") == "yes":
            add("SSHD-EMPTYPW", "sshd aceita senhas vazias", 4, "", "PermitEmptyPasswords no")
        if cf.get("permitrootlogin") == "yes":
            add("SSHD-ROOT", "sshd permite login direto como root", 3, "", "PermitRootLogin no (ou prohibit-password)")
        if cf.get("passwordauthentication") == "yes":
            add("SSHD-PASSWD", "sshd aceita autenticação por senha", 2, "", "use só chaves: PasswordAuthentication no")
    return fs, {}, "\n".join(raw)
