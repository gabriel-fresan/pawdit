"""Tiny Markdown -> ANSI renderer (stdlib only). Covers what pawdit and the LLM emit; falls back to raw text."""

import re
import textwrap

from .util import _COLOR_ON, paint, term_width

SEV_COLORS = {"CRÍTICO": "1;97;41", "ALTO": "1;31", "MÉDIO": "1;33", "BAIXO": "36", "INFO": "2"}
_SEV_RE = re.compile(r"\b(CRÍTICO|ALTO|MÉDIO|BAIXO|INFO)\b")
_INLINE = re.compile(r"`([^`]+)`|\*\*([^*]+)\*\*|(?<![*\w])\*([^*\n]+)\*(?!\w)|_([^_\n]+)_(?!\w)")
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def vlen(s):
    return len(_ANSI.sub("", s))


def inline(s):
    def rep(m):
        if m.group(1) is not None:
            return paint("38;5;180", m.group(1))
        if m.group(2) is not None:
            return paint("1", m.group(2))
        return paint("3", m.group(3) or m.group(4))

    return _SEV_RE.sub(lambda m: paint(SEV_COLORS[m.group(1)], m.group(1)), _INLINE.sub(rep, s))


def _wrap(text, width, first, rest):
    """Wrap plain text (before styling) and style each line; indent prefixes are already styled."""
    plain = _INLINE.sub(lambda m: next(g for g in m.groups() if g is not None), text)
    if len(plain) <= width - vlen(first):
        return [first + inline(text)]
    lines = textwrap.wrap(text, max(20, width - vlen(first)), break_long_words=False, break_on_hyphens=False)
    return [(first if i == 0 else rest) + inline(ln) for i, ln in enumerate(lines)] or [first]


def render(md, width=None):
    """Return ANSI-styled text, or the raw markdown when colour is off (pipes, NO_COLOR)."""
    if not _COLOR_ON():
        return md
    width = min(width or term_width(), 100)
    out, fence = [], False
    for raw in md.splitlines():
        line = raw.rstrip()
        if line.lstrip().startswith("```"):
            fence = not fence
            out.append(paint("2", "  ┌" + "─" * 20 if fence else "  └" + "─" * 20))
            continue
        if fence:
            out.append(paint("2", "  │ ") + paint("38;5;151", line))
            continue
        if not line.strip():
            out.append("")
            continue
        if m := re.match(r"^(#{1,6})\s+(.*)", line):
            lvl, txt = len(m.group(1)), m.group(2)
            if lvl == 1:
                out += [paint("1;95", txt.upper()), paint("95", "━" * min(width, max(len(txt), 20)))]
            elif lvl == 2:
                out += ["", paint("1;96", "▌ " + txt)]
            else:
                out += ["", paint("1;94", "◆ ") + inline(txt)]
            continue
        if re.match(r"^\s*([-*_])\1{2,}\s*$", line):
            out.append(paint("2", "─" * min(width, 60)))
            continue
        if m := re.match(r"^>\s?(.*)", line):
            bar = paint("35", "▏ ")
            out += [bar + x for x in _wrap(m.group(1), width - 2, "", "")]
            continue
        if m := re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)", line):
            ind = " " * len(m.group(1))
            mark = paint("36", "•") if m.group(2) in "-*+" else paint("36", m.group(2))
            out += _wrap(m.group(3), width, f"{ind}{mark} ", f"{ind}  ")
            continue
        out += _wrap(line.strip(), width, "", "")
    return "\n".join(out)
