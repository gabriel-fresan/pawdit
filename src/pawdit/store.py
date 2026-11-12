from __future__ import annotations

import os

from .config import paths
from .report import render_report
from .util import die, jload, jsave


def write_run(rdir, run, findings):
    jsave(os.path.join(rdir, "findings.json"), findings)
    jsave(os.path.join(rdir, "run.json"), run)
    with open(os.path.join(rdir, "report.md"), "w", encoding="utf-8") as fh:
        fh.write(render_report(run, findings))


def secure_tree(root, group):
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
            os.chmod(p, 0o750 if os.path.isdir(p) else 0o640)
            if gid is not None:
                os.chown(p, 0, gid)
    os.chmod(root, 0o750)
    if gid is not None:
        os.chown(root, 0, gid)


def load_latest(cfg):
    P = paths(cfg)
    run = jload(os.path.join(P["latest"], "run.json"))
    fs = jload(os.path.join(P["latest"], "findings.json"), [])
    return run, fs


def need_latest(cfg):
    run, fs = load_latest(cfg)
    if not run:
        die("nenhuma auditoria encontrada (ou sem permissão de leitura). Rode: sudo pawdit run")
    return run, fs
