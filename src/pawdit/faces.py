"""Cat faces by mood. Big (3-line, greeting) and inline (one-line headers) variants share one table.

Moods, calm to grim: ok ^ · low - · medium O · worried (high) · alarm (high and new) · crit X.
Extras: sleepy (stale audit) and curious (first run).
"""

from .models import SEV_COLOR
from .util import paint

# mood -> (face for the 3-line cat, inline cat, colour)
MOODS = {
    "ok": ("^▾^", "/ᐠ ·^ ▾  ^マ", "32"),
    "low": ("-▾-", "/ᐠ ·- ▾ -マ", "36"),
    "medium": ("OꞈO", "/ᐠ ·O ▾  Oマ", SEV_COLOR[2]),
    "worried": ("•᷄△•᷅", "/ᐠ ·•᷄ ˕  •᷅マ", SEV_COLOR[3]),
    "alarm": ("°△°", "/ᐠ  ╥ ▾  ╥マ", "1;31"),
    "crit": ("X¬X", "/ᐠ ·X ▾  Xマ", SEV_COLOR[4]),
    "sleepy": ("˘▾˘", "/ᐠ ·˘ ▾  ˘マ", "2"),
    "curious": ("◕▾◕", "/ᐠ ·◕ ▾  ◕マ", "35"),
}


def mood(counts, new_high=False, stale=False, first_run=False):
    """Pick a mood from the severity counts ({"4": n, ...}) plus context flags."""
    if stale:
        return "sleepy"
    if first_run:
        return "curious"
    c = {k: int(v) for k, v in counts.items()}
    if c.get("4"):
        return "crit"
    if c.get("3"):
        return "alarm" if new_high else "worried"
    if c.get("2"):
        return "medium"
    return "low" if c.get("1") else "ok"


def big(m):
    return [" /\\_/\\  ", f"( {MOODS[m][0]} ) ", " > ^ <  "]


def inline(m):
    return MOODS[m][1]


def color(m):
    return MOODS[m][2]


def banner(m, text=""):
    """One-line header for list/diff/history/doctor: coloured inline cat + optional text."""
    return paint(color(m), inline(m)) + (" " + paint("1", text) if text else "")
