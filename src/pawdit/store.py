from __future__ import annotations

import os

from .config import paths, resolve_group
from .report import render_report
from .util import die, jload, jsave


def write_run(rdir, run, findings):
    jsave(os.path.join(rdir, "findings.json"), findings)
    jsave(os.path.join(rdir, "run.json"), run)
    with open(os.path.join(rdir, "report.md"), "w", encoding="utf-8") as fh:
        fh.write(render_report(run, findings))


def _chgrp(path, gid):
    """Hand the path to the admin group; as a non-root member only the group can change (and may be refused)."""
    if gid is None:
        return
    try:
        os.chown(path, 0 if os.geteuid() == 0 else -1, gid)
    except PermissionError:
        pass


def secure_tree(root, group):
    """State is group-accessible (rw): the group is the admin group (wheel/sudo), which already has root via sudo."""
    gid = None
    if group:
        try:
            import grp

            gid = grp.getgrnam(group).gr_gid
        except (ImportError, KeyError):
            pass
    for dp, dn, fn in os.walk(root):
        for name in dn + fn:
            p = os.path.join(dp, name)
            if os.path.islink(p):
                continue
            os.chmod(p, 0o2770 if os.path.isdir(p) else 0o660)
            _chgrp(p, gid)
    os.chmod(root, 0o2770)  # setgid: arquivos novos herdam o grupo
    _chgrp(root, gid)


def load_latest(cfg):
    P = paths(cfg)
    run = jload(os.path.join(P["latest"], "run.json"))
    fs = jload(os.path.join(P["latest"], "findings.json"), [])
    return run, fs


def need_latest(cfg):
    run, fs = load_latest(cfg)
    if not run:
        P = paths(cfg)
        if os.path.isdir(P["state"]) and not os.access(P["state"], os.R_OK):
            die(f"sem permissão em {P['state']}: seu usuário precisa estar no grupo '{resolve_group(cfg) or 'admin'}'")
        die("nenhuma auditoria encontrada. Rode: sudo pawdit run")
    return run, fs
