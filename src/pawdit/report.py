from __future__ import annotations

from .models import SEV


def fmt_finding(f, md=True):
    st = "novo" if f.get("new") else f"desde {f.get('first_seen', '?')}"
    L = [f"### #{f['n']} · {SEV[f['sev']].upper()} · {f['tool']}/{f['id']} · {st}", "", f"**{f['title']}**", ""]
    if f["detail"]:
        L.append(f"- Detalhe: {f['detail']}")
    if f["hint"]:
        L.append(f"- Sugestão da ferramenta: {f['hint']}")
    L.append("")
    if f.get("ai"):
        L += ["> [IA — modelo pequeno local; confira antes de aplicar]", "", f["ai"], ""]
    else:
        L += [
            "_(sem texto de IA para este achado — use `pawdit fix {n} --gen` ou `pawdit ai`)_".replace(
                "{n}", str(f["n"])
            ),
            "",
        ]
    return "\n".join(L)


def render_report(run, findings):
    ts = run["ts"][:16].replace("T", " ")
    L = [
        f"# pawdit — {run['host']}",
        "",
        f"_{ts} · {run['os']['name']} · {'IA: ' + run['model'] if run.get('ai_ok') else 'sem texto de IA'}_",
        "",
    ]
    if run.get("score") is not None:
        d = run.get("prev_score")
        L.append(
            f"**Hardening index:** {run['score']}" + (f" ({run['score'] - d:+d} vs. anterior)" if d is not None else "")
        )
    c = run["counts"]
    L += [
        f"**Achados:** {c['4']} críticos · {c['3']} altos · {c['2']} médios · {c['1']} baixos · {c['0']} info",
        "",
        "## Resumo",
        "",
        run["brief"]["resumo"] or "—",
        "",
    ]
    if run["brief"]["dicas"]:
        L += ["## Melhorias rápidas", ""] + [f"- #{d['n']}: {d['dica']}" for d in run["brief"]["dicas"]] + [""]
    L += ["## Mudanças desde a última auditoria", ""]
    if run.get("first_run"):
        L.append("Primeira auditoria: serve de baseline.")
    else:
        L.append(f"- Novos: {sum(1 for f in findings if f.get('new'))}")
        L += [f"- Resolvido: {r['tool']}/{r['id']} — {r['title']}" for r in run.get("resolved", [])[:30]] or [
            "- Nada resolvido."
        ]
    L += ["", "## Achados", ""] + [fmt_finding(f) for f in findings]
    L += ["## Ferramentas", ""] + [
        f"- {k}: {v['status']}" + (f" ({v['msg']})" if v.get("msg") else "") for k, v in run["tools"].items()
    ]
    return "\n".join(L) + "\n"
