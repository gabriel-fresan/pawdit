from __future__ import annotations

import json
import os
import re
import shutil
import sys

from . import __version__
from .ai import do_ai, gen_fix
from .audit import run_audit
from .config import paths, resolve_group
from .greet import render_greet
from .models import SEV, SEV_COLOR
from .report import fmt_finding
from .store import load_latest, need_latest, secure_tree, write_run
from .util import age_days, die, jload, log, one_line, os_info, page, paint, term_width, trunc


def cmd_run(cfg, a):
    run_audit(cfg, no_ai=a.no_ai, only=a.only, model=a.model, max_ai=a.max)


def cmd_ai(cfg, a):
    """Regenerate AI texts. Needs write access to the state dir (root or the admin group), not a full audit."""
    P = paths(cfg)
    if not os.access(P["state"], os.W_OK):
        die(f"sem escrita em {P['state']}: use sudo ou entre no grupo '{resolve_group(cfg) or 'admin'}'")
    os.umask(0o007)  # new files stay group-accessible
    if a.model:
        cfg["model"] = a.model
    if a.max:
        cfg["max_ai_findings"] = a.max
    run, fs = need_latest(cfg)
    rdir = os.path.realpath(P["latest"])
    do_ai(cfg, run, fs, checkpoint=lambda: write_run(rdir, run, fs))
    write_run(rdir, run, fs)
    if os.geteuid() == 0:
        secure_tree(P["state"], resolve_group(cfg))


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
        page(fh.read(), md=True)


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
    page(fmt_finding(f), md=True)


def cmd_fix(cfg, a):
    run, fs = need_latest(cfg)
    if a.ref:
        f = find_one(fs, a.ref)
        if not f:
            die(f"achado '{a.ref}' não encontrado (veja: pawdit list)")
        return show_fix(cfg, run, fs, f, a.gen)
    return show_overview(cfg, run, fs, a)


def fix_steps(f):
    """The 'Como corrigir' block of the AI text, or the tool's own hint as fallback."""
    m = re.search(r"\*\*Como corrigir:?\*\*:?\s*(.*?)(?=\n\s*\*\*[^*\n]+:?\*\*|\Z)", f.get("ai") or "", re.S)
    txt = m.group(1).strip() if m else ""
    return txt or (f.get("hint") and f"_(sem texto de IA)_ {f['hint']}") or "_(sem sugestão — rode `pawdit fix --gen`)_"


def show_overview(cfg, run, fs, a):
    """All findings with the AI's short fix each, rendered; --gen fills in missing texts (slow on CPU)."""
    shown = fs[: a.max or 20]
    if a.gen:
        todo = [f for f in shown if not f.get("ai")]
        for i, f in enumerate(todo, 1):
            log(f"gerando {i}/{len(todo)}: {trunc(f['title'], 50)}")
            try:
                f["ai"] = gen_fix(cfg, run["os"], f)
            except Exception as e:  # noqa: BLE001
                print(f"IA indisponível: {one_line(e, 160)}", file=sys.stderr)
                break
        if todo and os.access(paths(cfg)["state"], os.W_OK):
            write_run(os.path.realpath(paths(cfg)["latest"]), run, fs)
    parts = ["# pawdit · soluções\n"]
    for f in shown:
        parts.append(f"### #{f['n']} · {SEV[f['sev']].upper()} · {f['title']}\n\n{fix_steps(f)}\n")
    if len(fs) > len(shown):
        parts.append(f"_… mais {len(fs) - len(shown)} achados (use `--max`)._\n")
    parts.append("---\n_Detalhe completo: `pawdit fix N`_")
    page("\n".join(parts), md=True)


def cmd_diff(cfg, a):
    run, fs = need_latest(cfg)
    if run.get("first_run"):
        print("primeira auditoria: ainda não há com o que comparar")
        return
    for f in fs:
        if f.get("new"):
            print(
                paint("1;31", "+ ")
                + paint(SEV_COLOR[f["sev"]], f"#{f['n']} {SEV[f['sev']]:<7}")
                + paint("2", f" {f['tool']}/{f['id']} ")
                + trunc(f["title"], term_width() - 36)
            )
    for r in run.get("resolved", []):
        print(
            paint("1;32", "- ")
            + paint("2;9", f"{r['tool']}/{r['id']}")
            + paint("32", f" resolvido · {trunc(r['title'], term_width() - 30)}")
        )
    if not any(f.get("new") for f in fs) and not run.get("resolved"):
        print(paint("32", "✓ sem mudanças desde a última auditoria"))


def cmd_history(cfg, a):
    P = paths(cfg)
    try:
        names = sorted(os.listdir(P["hist"]))
    except OSError:
        die("sem histórico (ou sem permissão)")
    print(paint("1;36", f"{'data':<17} {'score':>5}  crit alto méd baixo  novos"))
    for n in names[-a.n :]:
        r = jload(os.path.join(P["hist"], n, "run.json"))
        if r:
            c = r["counts"]
            sc = "-" if r.get("score") is None else r["score"]
            scp = paint(
                "32" if isinstance(sc, int) and sc >= 80 else "33" if isinstance(sc, int) and sc >= 60 else "31",
                f"{sc:>5}",
            )
            cols = [
                paint(SEV_COLOR[s] if c[str(s)] else "2", f"{c[str(s)]:>{w}}")
                for s, w in ((4, 4), (3, 4), (2, 3), (1, 5))
            ]
            nc = r.get("new_count", "-")
            print(
                f"{r['ts'][:16].replace('T', ' '):<17} {scp}  {' '.join(cols)}  "
                + paint("1;33" if nc not in (0, "-") else "2", f"{nc:>5}")
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

    print(
        paint("1;35", f"pawdit {__version__}")
        + f" >:3 python {sys.version.split()[0]} · {os_info()['name']} ({os_info()['kind']})"
    )
    for t in ("lynis", "ssh-audit", "aide", "chkrootkit", "vulnix", "trivy", "aureport", "docker", "podman"):
        p = shutil.which(t)
        print(
            f"  {paint('32', '✓') if p else paint('2', '·')} {t:<11} "
            + (paint("2", p) if p else paint("33", "não encontrado (coletor será ignorado)"))
        )
    try:
        with urllib.request.urlopen(cfg["ollama_url"].rstrip("/") + "/api/tags", timeout=5) as r:
            names = [m["name"] for m in json.load(r).get("models", [])]
        ok = cfg["model"] in names or cfg["model"] + ":latest" in names
        print(
            f"  {paint('32', '✓') if ok else paint('1;31', '✗')} ollama {cfg['ollama_url']} — modelo {cfg['model']}"
            + ("" if ok else f"  → ollama pull {cfg['model']}")
        )
    except Exception as e:  # noqa: BLE001
        print(f"  {paint('1;31', '✗')} ollama {cfg['ollama_url']} inacessível ({one_line(e, 80)})")
    g = resolve_group(cfg)
    if os.access(cfg["state_dir"], os.R_OK):
        print(f"  {paint('32', '✓')} estado {cfg['state_dir']} legível (grupo {g or '-'})")
    else:
        print(
            f"  {paint('1;31', '✗')} estado {cfg['state_dir']} sem acesso — adicione seu usuário ao grupo '{g or 'admin'}' (sudo usermod -aG {g or 'GRUPO'} $USER)"
        )
