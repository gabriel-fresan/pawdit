import json

from pawdit.ai import do_ai, gen_brief, ollama_chat
from pawdit.models import F

RUN = {"os": {"name": "Test OS", "kind": "tradicional"}, "score": 61, "resolved": []}


def findings():
    fs = [F("lynis", f"ID-{i}", f"problema {i}", 3 - (i % 3), hint=f"corrigir {i}") for i in range(5)]
    for i, f in enumerate(fs, 1):
        f["n"], f["new"] = i, False
    return fs


def responder(body):
    if "format" in body:
        return json.dumps({"resumo": "O sistema apresenta alto risco de segurança devido a " + "problemas " * 30})
    return "- **Reiniciar o sistema para aplicar a correção do kernel e depois revisar tudo isso aqui**\noutra linha"


def test_request_never_carries_tools(cfg, ollama):
    ollama.responder = lambda b: "texto"
    ollama_chat(cfg, "oi")
    assert "tools" not in ollama.requests[0] and "functions" not in ollama.requests[0]
    assert ollama.requests[0]["stream"] is False


def test_think_param_is_dropped_when_model_rejects_it(cfg, ollama):
    ollama.responder = lambda b: (400, "does not support thinking") if "think" in b else "ok"
    assert ollama_chat(cfg, "oi") == "ok"
    assert "think" in ollama.requests[0] and "think" not in ollama.requests[1]


def test_think_blocks_are_removed(cfg, ollama):
    ollama.responder = lambda b: "<think>segredo</think>resposta"
    assert ollama_chat(cfg, "oi") == "resposta"


def test_brief_is_short_and_tips_are_bound_to_real_findings(cfg, ollama):
    ollama.responder = responder
    fs = findings()
    brief = gen_brief(cfg, RUN, fs)
    assert len(brief["resumo"]) <= 131 and brief["resumo"].endswith("…")
    assert [d["n"] for d in brief["dicas"]] == [1, 2, 3]  # tips follow the findings, not the model's pick
    assert all(len(d["dica"]) <= 57 and "*" not in d["dica"] and "\n" not in d["dica"] for d in brief["dicas"])


def test_each_tip_prompt_only_contains_its_own_finding(cfg, ollama):
    ollama.responder = responder
    gen_brief(cfg, RUN, findings())
    tip_prompts = [r["messages"][1]["content"] for r in ollama.requests if "format" not in r]
    assert len(tip_prompts) == 3
    assert "problema 0" in tip_prompts[0] and "problema 1" not in tip_prompts[0]


def test_do_ai_falls_back_when_ollama_is_down(cfg):
    cfg["ollama_url"] = "http://127.0.0.1:1"
    run, fs = dict(RUN), findings()
    do_ai(cfg, run, fs)
    assert run["ai_ok"] is False and run["brief"]["resumo"] and not any("ai" in f for f in fs)


def test_fix_texts_are_cached_between_runs(cfg, ollama):
    ollama.responder = responder
    cfg["max_ai_findings"] = 2
    import os

    os.makedirs(cfg["state_dir"], exist_ok=True)
    run, fs = dict(RUN), findings()
    do_ai(cfg, run, fs)
    first_calls = len(ollama.requests)
    do_ai(cfg, dict(RUN), findings())
    new_calls = len(ollama.requests) - first_calls
    assert new_calls == 1 + 3  # brief + tips are regenerated; the 2 fix texts come from the cache


def test_ai_output_is_sanitized(cfg, ollama):
    import os

    os.makedirs(cfg["state_dir"], exist_ok=True)
    ollama.responder = lambda b: json.dumps({"resumo": "ok"}) if "format" in b else "x\x1b]0;PWN\x07y\x1b[31mz"
    cfg["max_ai_findings"] = 1
    run, fs = dict(RUN), findings()
    do_ai(cfg, run, fs)
    assert "\x1b" not in fs[0]["ai"] and "\x07" not in fs[0]["ai"]
