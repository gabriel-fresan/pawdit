import re

from pawdit.config import DEFAULTS
from pawdit.greet import render_greet

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def make_run(**kw):
    run = {
        "ts": "2026-11-12T03:30:00",
        "host": "home-server",
        "score": 63,
        "prev_score": 60,
        "first_run": False,
        "counts": {"4": 0, "3": 3, "2": 17, "1": 119, "0": 0},
        "resolved": [{}] * 4,
        "ai_ok": True,
        "brief": {
            "resumo": "O sistema apresenta alto risco de segurança devido a problemas críticos como falta de "
            "sincronização de tempo e kernel desatualizado, além de SSH com senha habilitada.",
            "dicas": [
                {"n": 1, "dica": "Reiniciar para aplicar o kernel novo"},
                {"n": 2, "dica": "Desativar login por senha no SSH"},
            ],
        },
    }
    run.update(kw)
    return run


FS = [{"n": 1, "id": "KRNL-5830", "sev": 3, "new": True}, {"n": 2, "id": "SSH-1", "sev": 2, "new": False}]


def test_greet_respects_size_limits():
    out = ANSI.sub("", render_greet(DEFAULTS, make_run(), FS, 200))
    lines = out.splitlines()
    assert len(lines) <= 10
    assert max(len(line) for line in lines) <= DEFAULTS["greet_width"]


def test_summary_is_cut_on_a_word_with_ellipsis_and_fits_two_lines():
    out = ANSI.sub("", render_greet(DEFAULTS, make_run(), FS, 80))
    summary = [line for line in out.splitlines() if line.startswith(("ia ▸", "      "))]
    assert len(summary) == 2 and summary[-1].endswith("…")


def test_narrow_terminal_is_respected():
    out = ANSI.sub("", render_greet(DEFAULTS, make_run(), FS, 50))
    assert max(len(line) for line in out.splitlines()) <= 50


def test_first_run_and_stale_and_no_ai_notes():
    out = ANSI.sub("", render_greet(DEFAULTS, make_run(first_run=True, ts="2020-01-01T00:00:00", ai_ok=False), FS, 80))
    assert "primeira auditoria" in out and "dias" in out and "IA indisponível" in out


def test_face_depends_on_severity():
    calm = make_run(counts={"4": 0, "3": 0, "2": 0, "1": 2, "0": 0})
    nothing = make_run(counts={"4": 0, "3": 0, "2": 0, "1": 0, "0": 0})
    assert "^▾^" in render_greet(DEFAULTS, nothing, [], 80)
    assert "-▾-" in render_greet(DEFAULTS, calm, [], 80)
    assert "OꞈO" in render_greet(DEFAULTS, make_run(counts={"4": 0, "3": 0, "2": 1, "1": 0, "0": 0}), FS, 80)
    assert "•᷄△•᷅" in render_greet(DEFAULTS, make_run(), [], 80)  # high, nothing new
    assert "°△°" in render_greet(DEFAULTS, make_run(), [{**FS[0], "new": True, "sev": 3}], 80)  # high and new
    assert "X¬X" in render_greet(DEFAULTS, make_run(counts={"4": 1, "3": 0, "2": 0, "1": 0, "0": 0}), FS, 80)
    assert "˘▾˘" in render_greet(DEFAULTS, make_run(ts="2020-01-01T00:00:00"), FS, 80)  # stale audit
    assert "◕▾◕" in render_greet(DEFAULTS, make_run(first_run=True), FS, 80)


def test_inline_faces():
    from pawdit import faces

    assert [faces.inline(m) for m in ("ok", "low", "medium", "worried", "alarm", "crit")] == [
        "/ᐠ ·^ ▾  ^マ",
        "/ᐠ ·- ▾ -マ",
        "/ᐠ ·O ▾  Oマ",
        "/ᐠ ·•᷄ ˕  •᷅マ",
        "/ᐠ  ╥ ▾  ╥マ",
        "/ᐠ ·X ▾  Xマ",
    ]


def test_help_command_and_flags(capsys):
    import pytest

    from pawdit.cli import main

    assert main(["help"]) == 0
    out = capsys.readouterr().out
    assert "exemplos" in out and "pawdit fix 3" in out and "/ᐠ" in out
    with pytest.raises(SystemExit) as e:
        main(["--help"])
    assert e.value.code == 0 and "exemplos" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["fix", "--help"])
    assert "--gen" in capsys.readouterr().out
    assert main(["help", "fix"]) == 0 and "--gen" in capsys.readouterr().out
    assert main(["help", "nada"]) == 0 and "não existe" in capsys.readouterr().err
