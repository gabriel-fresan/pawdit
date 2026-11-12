from __future__ import annotations

import json
import os
import shutil
import sys

from . import __version__
from .ai import do_ai, gen_fix
from .audit import run_audit
from .config import paths
from .greet import render_greet
from .models import SEV, SEV_COLOR
from .report import fmt_finding
from .store import load_latest, need_latest, secure_tree, write_run
from .util import age_days, die, jload, log, one_line, os_info, page, paint, term_width, trunc


def cmd_run(cfg, a):
    run_audit(cfg, no_ai=a.no_ai, only=a.only, model=a.model, max_ai=a.max)


def cmd_ai(cfg, a):
    if os.geteuid() != 0 and not os.environ.get("PAWDIT_ALLOW_USER"):
        die("rode como root: sudo pawdit ai")
    if a.model:
        cfg["model"] = a.model
    if a.max:
        cfg["max_ai_findings"] = a.max
    run, fs = need_latest(cfg)
    rdir = os.path.realpath(paths(cfg)["latest"])
    do_ai(cfg, run, fs, checkpoint=lambda: write_run(rdir, run, fs))
    write_run(rdir, run, fs)
    secure_tree(paths(cfg)["state"], cfg.get("state_group"))


def cmd_greet(cfg, a):
    try:
        if not (sys.stdout.isatty() or a.force):
            return
        run, fs = load_latest(cfg)
        if not run:
            if os.path.isdir(cfg["state_dir"]) and os.access(cfg["state_dir"], os.R_OK):
                print(paint("2", "pawdit: ainda sem auditorias — sudo pawdit run"))
            return
        print(render_greet(cfg, run, fs, term_width()))
    except Exception:  # noqa: BLE001  (o greeting nunca pode quebrar o login)
        return


def cmd_report(cfg, a):
    P = paths(cfg)
    need_latest(cfg)
    with open(os.path.join(P["latest"], "report.md"), encoding="utf-8") as fh:
        page(fh.read())


def cmd_list(cfg, a):
    run, fs = need_latest(cfg)
    w = term_width()
    for f in fs:
        if a.new and not f.get("new"):
            continue
        if a.min_sev and f["sev"] < a.min_sev:
            continue
        st = "novo" if f.get("new") else f"{age_days(f.get('first_seen', '') + 'T00:00:00')}d"
        left = f"{f['n']:>3} "
        tag = paint(SEV_COLOR[f["sev"]], f"{SEV[f['sev']]:<7}")
        rest = f" {st:<5} {f['id'][:16]:<16} "
        print(left + tag + rest + trunc(f["title"], max(10, w - len(left) - 7 - len(rest))))


def find_one(fs, ref):
    if ref.isdigit():
        return next((f for f in fs if f["n"] == int(ref)), None)
    m = [f for f in fs if f["id"].lower() == ref.lower()]
    return m[0] if m else None


def show_fix(cfg, run, fs, f, gen):
    if gen and not f.get("ai"):
        try:
            log("gerando texto com o modelo…")
            f["ai"] = gen_fix(cfg, run["os"], f)
        except Exception as e:  # noqa: BLE001
            print(f"IA indisponível: {one_line(e, 160)}", file=sys.stderr)
    page(fmt_finding(f))


def cmd_fix(cfg, a):
    run, fs = need_latest(cfg)
    if a.ref:
        f = find_one(fs, a.ref)
        if not f:
            die(f"achado '{a.ref}' não encontrado (veja: pawdit list)")
        return show_fix(cfg, run, fs, f, a.gen)
    # menu compacto: lista os 15 primeiros e pede um número
    while True:
        print()
        for f in fs[:15]:
            print(
                f"{f['n']:>3} "
                + paint(SEV_COLOR[f["sev"]], f"{SEV[f['sev']]:<7}")
                + f" {trunc(f['title'], term_width() - 14)}"
            )
        try:
            ans = input(paint("35", "número (enter sai) >:3 ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not ans:
            return
        f = find_one(fs, ans)
        if f:
            show_fix(cfg, run, fs, f, a.gen)
        else:
            print("não achei esse número")


def cmd_diff(cfg, a):
    run, fs = need_latest(cfg)
    if run.get("first_run"):
        print("primeira auditoria: ainda não há com o que comparar")
        return
    for f in fs:
        if f.get("new"):
            print(
                paint("31", "+ ")
                + f"#{f['n']} [{SEV[f['sev']]}] {f['tool']}/{f['id']} — {trunc(f['title'], term_width() - 30)}"
            )
    for r in run.get("resolved", []):
        print(paint("32", "- ") + f"{r['tool']}/{r['id']} — {trunc(r['title'], term_width() - 25)}")
    if not any(f.get("new") for f in fs) and not run.get("resolved"):
        print("sem mudanças desde a última auditoria")


def cmd_history(cfg, a):
    P = paths(cfg)
    try:
        names = sorted(os.listdir(P["hist"]))
    except OSError:
        die("sem histórico (ou sem permissão)")
    print(f"{'data':<17} {'score':>5}  crit alto méd baixo  novos")
    for n in names[-a.n :]:
        r = jload(os.path.join(P["hist"], n, "run.json"))
        if r:
            c = r["counts"]
            sc = "-" if r.get("score") is None else r["score"]
            print(
                f"{r['ts'][:16].replace('T', ' '):<17} {sc:>5}  {c['4']:>4} {c['3']:>4} {c['2']:>3} {c['1']:>5}  {r.get('new_count', '-'):>5}"
            )


def cmd_raw(cfg, a):
    P = paths(cfg)
    d = os.path.join(P["latest"], "raw")
    try:
        have = sorted(x[:-4] for x in os.listdir(d))
    except OSError:
        die("sem auditorias")
    if not a.tool or a.tool not in have:
        die("ferramentas com saída bruta: " + ", ".join(have))
    with open(os.path.join(d, a.tool + ".txt"), encoding="utf-8") as fh:
        page(fh.read())


def cmd_doctor(cfg, a):
    import urllib.request

    print(f"pawdit {__version__} · python {sys.version.split()[0]} · {os_info()['name']} ({os_info()['kind']})")
    for t in ("lynis", "ssh-audit", "aide", "chkrootkit", "vulnix", "trivy", "aureport", "bat"):
        p = shutil.which(t)
        print(f"  {'✓' if p else '·'} {t:<11} {p or 'não encontrado (coletor será ignorado)'}")
    try:
        with urllib.request.urlopen(cfg["ollama_url"].rstrip("/") + "/api/tags", timeout=5) as r:
            names = [m["name"] for m in json.load(r).get("models", [])]
        ok = cfg["model"] in names or cfg["model"] + ":latest" in names
        print(
            f"  {'✓' if ok else '✗'} ollama {cfg['ollama_url']} — modelo {cfg['model']}"
            + ("" if ok else f"  → ollama pull {cfg['model']}")
        )
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ ollama {cfg['ollama_url']} inacessível ({one_line(e, 80)})")
    print(f"  estado: {cfg['state_dir']} ({'legível' if os.access(cfg['state_dir'], os.R_OK) else 'sem acesso'})")
