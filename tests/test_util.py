from pawdit.util import cut_words, one_line, safe_text, trunc


def test_safe_text_strips_terminal_escapes_and_bidi():
    dirty = "a\x1b[31mb\x1b]0;title\x07c‮d\r\x00e"
    out = safe_text(dirty)
    assert "\x1b" not in out and "\x07" not in out and "‮" not in out and "\r" not in out
    assert out.startswith("ab") and out.endswith("de")


def test_safe_text_keeps_newlines():
    assert safe_text("a\nb") == "a\nb"


def test_one_line_collapses_and_limits():
    assert one_line("a \n  b\t c") == "a b c"
    assert len(one_line("x" * 500, 50)) == 50


def test_cut_words_breaks_on_word_boundary():
    out = cut_words("um dois três quatro cinco seis", 18)
    assert out.endswith("…") and " " not in out[-2:] and len(out) <= 19
    assert cut_words("curto", 18) == "curto"


def test_trunc():
    assert trunc("abcdef", 4) == "abc…" and trunc("abc", 4) == "abc"
