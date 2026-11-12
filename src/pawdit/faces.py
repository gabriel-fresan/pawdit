"""Cat faces by worst severity: ^ ok · O medium · worried high · X critical. Big (3 lines) and inline variants."""

from .models import SEV_COLOR
from .util import paint

EYES = {0: ("^", "^"), 1: ("^", "^"), 2: ("O", "O"), 3: ("•᷄", "•᷅"), 4: ("X", "X")}
COLOR = {0: "32", 1: "32", 2: SEV_COLOR[2], 3: SEV_COLOR[3], 4: SEV_COLOR[4]}


def level(counts):
    """Worst severity present in a ``{"4": n, ...}`` counts dict (low/info count as calm)."""
    for s in (4, 3, 2):
        if int(counts.get(str(s), 0)):
            return s
    return 0


def big(lvl):
    le, re_ = EYES[lvl]
    return [" /\\_/\\  ", f"( {le}˕{re_} ) ", " > ^ <  "]


def inline(lvl):
    le, re_ = EYES[lvl]
    return f"/ᐠ ·{le} ˕  {re_}マ"


def banner(lvl, text=""):
    """One-line header for list/diff/history/doctor: coloured inline cat + optional text."""
    return paint(COLOR[lvl], inline(lvl)) + (" " + paint("1", text) if text else "")
