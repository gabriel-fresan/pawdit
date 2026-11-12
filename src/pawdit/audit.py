"""Audit orchestration: collect -> reconcile with the previous run -> AI text -> write state."""

from __future__ import annotations

import datetime as dt
import fcntl
import os
import shutil
import socket
import time
import types

from . import __version__
from .ai import do_ai, fallback_brief
from .collectors import COLLECTORS
from .config import paths
from .models import SEV
from .store import load_latest, secure_tree, write_run
from .util import die, log, one_line, os_info, safe_text


def collect(cfg, names, ctx, rdir):
    """Run the selected collectors. Returns (findings, tools_status, score)."""
    findings, tools, score = [], {}, None
    for name in names:
        fn = COLLECTORS.get(name)
        if not fn:
            continue
        log(f"coletando: {name}")
        t0 = time.time()
        try:
            res = fn(cfg, ctx)
        except Exception as e:  # noqa: BLE001 - one broken tool must not abort the audit
            tools[name] = {"status": "erro", "msg": one_line(e, 200)}
            log(f"{name}: erro — {one_line(e, 200)}")
            continue
        if res is None:
            tools[name] = {"status": "ausente"}
            continue
        fs, meta, raw = res
        findings += fs
        score = meta.get("score", score)
        tools[name] = {"status": "ok", "n": len(fs), "s": round(time.time() - t0)}
        with open(os.path.join(rdir, "raw", f"{name}.txt"), "w", encoding="utf-8") as fh:
            fh.write(safe_text(raw).replace("\r", "")[:2_000_000])
    return findings, tools, score


def reconcile(findings, prev_fs, prev_run, tools, today):
    """Merge with the previous run: dedupe, mark new/first_seen, carry findings of failed tools, rank, number.

    Returns (ranked_findings, resolved). Findings of tools that did not run OK this time are carried over
    (stale) instead of being reported as resolved.
    """
    uniq = {}
    for f in findings:
        uniq.setdefault(f["key"], f)
    for f in prev_fs:
        if tools.get(f["tool"], {}).get("status") != "ok" and f["key"] not in uniq:
            uniq[f["key"]] = dict(f, new=False, stale=True)
    prev = {f["key"]: f for f in prev_fs}
    out = list(uniq.values())
    for f in out:
        p = prev.get(f["key"])
        f["first_seen"] = p["first_seen"] if p else today
        f["new"] = bool(prev_run) and p is None  # the first run is a baseline, nothing is "new"
        f.pop("ai", None)
    out.sort(key=lambda f: (-f["sev"], not f["new"], f["tool"], f["id"]))
    for i, f in enumerate(out, 1):
        f["n"] = i
    cur = {f["key"] for f in out}
    resolved = [{k: p[k] for k in ("tool", "id", "title")} for p in prev_fs if p["key"] not in cur]
    return out, resolved


def run_audit(cfg, *, no_ai=False, only=None, model=None, max_ai=None):
    if os.geteuid() != 0 and not os.environ.get("PAWDIT_ALLOW_USER"):
        die("rode como root: sudo pawdit run")
    if model:
        cfg["model"] = model
    if max_ai:
        cfg["max_ai_findings"] = max_ai
    P = paths(cfg)
    os.makedirs(P["hist"], exist_ok=True)
    lock = open(P["lock"], "w")  # noqa: SIM115 - held until the process exits
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        die("já existe uma auditoria em andamento")

    now = dt.datetime.now()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    while os.path.exists(os.path.join(P["hist"], stamp)):  # two runs in the same second
        stamp += "x"
    rdir = os.path.join(P["hist"], stamp)
    os.makedirs(os.path.join(rdir, "raw"))
    ctx = types.SimpleNamespace(tmp=os.path.join(rdir, "tmp"), os=os_info())

    names = only.split(",") if only else cfg["tools"]
    findings, tools, score = collect(cfg, names, ctx, rdir)
    shutil.rmtree(ctx.tmp, ignore_errors=True)

    prev_run, prev_fs = load_latest(cfg)
    if score is None and prev_run and tools.get("lynis", {}).get("status") != "ok":
        score = prev_run.get("score")  # partial run (--only): keep the last hardening index
    findings, resolved = reconcile(findings, prev_fs, prev_run, tools, now.strftime("%Y-%m-%d"))

    run = {
        "version": __version__,
        "ts": now.isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "os": ctx.os,
        "score": score,
        "prev_score": (prev_run or {}).get("score"),
        "first_run": not prev_run,
        "counts": {str(s): sum(1 for f in findings if f["sev"] == s) for s in SEV},
        "new_count": sum(1 for f in findings if f["new"]),
        "resolved": resolved,
        "tools": tools,
        "model": None,
        "ai_ok": None,
        "brief": fallback_brief(findings, {}),
    }

    def activate():
        write_run(rdir, run, findings)
        tmp = P["latest"] + ".new"
        if os.path.lexists(tmp):
            os.unlink(tmp)
        os.symlink(os.path.join("history", stamp), tmp)
        os.replace(tmp, P["latest"])  # atomic: readers never see a half-written run

    activate()  # a usable (AI-less) report exists before spending CPU on the model
    if not no_ai:
        do_ai(cfg, run, findings, checkpoint=activate)
        activate()
    for old in sorted(os.listdir(P["hist"]))[: -cfg["history_keep"]]:
        shutil.rmtree(os.path.join(P["hist"], old), ignore_errors=True)
    secure_tree(P["state"], cfg.get("state_group"))
    log(f"ok — {len(findings)} achados, {len(resolved)} resolvidos, relatório em {P['latest']}/report.md")
