from pawdit import util
from pawdit.mdrender import render, vlen

MD = "# Titulo\n\n### #1 · ALTO · lynis/x\n\n**Bold** e `code` e _it_\n\n- item um\n> citação\n\n```\nls -l\n```\n"


def test_plain_when_no_color():
    util.set_color(False)
    assert render(MD) == MD


def test_styled_with_color():
    util.set_color(True)
    try:
        out = render(MD, width=60)
    finally:
        util.set_color(False)
    assert "\x1b[1mBold\x1b[0m" in out
    assert "**" not in out and "`" not in out and "###" not in out
    assert "•" in out and "▏" in out and "│ " in out
    assert "\x1b[1;31mALTO" in out


def test_wraps_to_width():
    util.set_color(True)
    try:
        out = render("- " + "palavra " * 40, width=50)
    finally:
        util.set_color(False)
    assert all(vlen(x) <= 50 for x in out.splitlines())
