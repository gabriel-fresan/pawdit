"""The compact summary shown at SSH login (limits: <=10 lines, <=greet_width columns)."""

from __future__ import annotations

import textwrap

from .models import SEV_COLOR
from .util import age_days, paint, trunc


def fit(segments, width):
    """Join (text, color) segments, truncating by *visible* width so ANSI codes never count."""
    out, left = [], width
    for text, code in segments:
        if left <= 0:
            break
        text = trunc(text, left)
        out.append(paint(code, text) if code else text)
        left -= len(text)
    return "".join(out)


def render_greet(cfg, run, fs, width):
    W = max(40, min(width, int(cfg["greet_width"])))
    c = run["counts"]
    hi, med = int(c["4"]) + int(c["3"]), int(c["2"])
    face = ">:3" if hi else ("o.o" if med else "^.^")
    art = [" /\\_/\\  ", f"( {face} ) ", " > ^ <  "]
    day = run["ts"][8:10] + "/" + run["ts"][5:7]
    age = age_days(run["ts"])
    head = f"pawdit · {run['host']} · {day} ({'hoje' if age == 0 else f'há {age}d'})"

    line2 = [(art[1], "34")]
    if run.get("score") is not None:
        d = run.get("prev_score")
        delta = f" ({run['score'] - d:+d})" if d not in (None, run["score"]) else ""
        line2.append((f"score {run['score']}{delta} · ", None))
    for sev, label in ((4, "crit"), (3, "alto"), (2, "méd"), (1, "baixo")):
        line2 += [(f"{c[str(sev)]} {label}", SEV_COLOR[sev]), (" ", None)]

    novos = sum(1 for f in fs if f.get("new"))
    novos_hi = sum(1 for f in fs if f.get("new") and f["sev"] >= 3)
    line3 = [(art[2], "34")]
    if run.get("first_run"):
        line3.append(("primeira auditoria (baseline)", None))
    else:
        line3.append((f"novos {novos}", None))
        if novos_hi:
            line3.append((f" (!{novos_hi} altos)", "1;31"))
        line3.append((f" · resolvidos {len(run.get('resolved', []))}", None))

    out = [fit([(art[0], "34"), (head, "1")], W), fit(line2, W), fit(line3, W)]
    if age > int(cfg["stale_days"]):
        out.append(fit([(f"⚠ auditoria com {age} dias — o timer está rodando?", "33")], W))

    resumo = run["brief"]["resumo"] or "sem resumo"
    if run.get("ai_ok") is False:
        resumo = "(IA indisponível) " + resumo
    wrapped = textwrap.wrap(textwrap.shorten(resumo, 2 * (W - 6) - 8, placeholder="…"), W - 6)[:2]
    for i, ln in enumerate(wrapped):
        out.append((paint("36", "ia ▸ ") if i == 0 else "      ") + ln)

    byn = {f["n"]: f for f in fs}
    for d in run["brief"]["dicas"][:3]:
        if d["n"] in byn:
            out.append(trunc(f"  #{d['n']} {d['dica']}", W))
    out.append(fit([("pawdit report · list · fix N · diff · history", "2")], W))
    return "\n".join(out)
