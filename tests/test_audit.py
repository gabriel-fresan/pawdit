import json
import os

import pytest

from pawdit import audit
from pawdit.audit import reconcile, run_audit
from pawdit.models import F


def mk(id_, sev=1, tool="fake"):
    return F(tool, id_, f"titulo {id_}", sev)


def ok(*tools):
    return {t: {"status": "ok"} for t in tools}


def test_first_run_is_a_baseline_nothing_is_new():
    out, resolved = reconcile([mk("A", 3), mk("B", 1)], [], None, ok("fake"), "2026-11-12")
    assert [f["id"] for f in out] == ["A", "B"] and [f["n"] for f in out] == [1, 2]
    assert not any(f["new"] for f in out) and resolved == []


def test_new_persisting_and_resolved():
    first, _ = reconcile([mk("A"), mk("B")], [], None, ok("fake"), "2026-11-01")
    second, resolved = reconcile([mk("B"), mk("C")], first, {"ts": "x"}, ok("fake"), "2026-11-08")
    by = {f["id"]: f for f in second}
    assert by["C"]["new"] and by["C"]["first_seen"] == "2026-11-08"
    assert not by["B"]["new"] and by["B"]["first_seen"] == "2026-11-01"  # first_seen survives
    assert [r["id"] for r in resolved] == ["A"]


def test_findings_of_a_failed_tool_are_carried_not_resolved():
    first, _ = reconcile([mk("A", tool="lynis"), mk("B", tool="fake")], [], None, ok("lynis", "fake"), "d1")
    tools = {"lynis": {"status": "erro", "msg": "boom"}, "fake": {"status": "ok"}}
    second, resolved = reconcile([mk("B", tool="fake")], first, {"ts": "x"}, tools, "d2")
    assert resolved == []
    carried = next(f for f in second if f["tool"] == "lynis")
    assert carried["stale"] and not carried["new"]


def test_ranking_severity_then_new_first():
    first, _ = reconcile([mk("old-high", 3)], [], None, ok("fake"), "d1")
    second, _ = reconcile([mk("old-high", 3), mk("new-high", 3), mk("low", 1)], first, {"ts": "x"}, ok("fake"), "d2")
    assert [f["id"] for f in second] == ["new-high", "old-high", "low"]


def test_duplicate_keys_are_collapsed():
    out, _ = reconcile([mk("A"), mk("A")], [], None, ok("fake"), "d")
    assert len(out) == 1


@pytest.fixture
def fake_collector(monkeypatch):
    state = {"findings": [mk("A", 3), mk("B", 1)]}

    def collect(cfg, ctx):
        return list(state["findings"]), {"score": 60}, "raw \x1b[31mred\x1b[0m output"

    monkeypatch.setitem(audit.COLLECTORS, "fake", collect)
    return state


def test_end_to_end_two_runs(cfg, fake_collector, monkeypatch):
    monkeypatch.setenv("PAWDIT_ALLOW_USER", "1")
    cfg["tools"] = ["fake"]
    run_audit(cfg, no_ai=True)
    latest = os.path.join(cfg["state_dir"], "latest")
    run = json.load(open(f"{latest}/run.json"))
    assert run["first_run"] and run["score"] == 60 and run["counts"]["3"] == 1
    assert "\x1b" not in open(f"{latest}/raw/fake.txt").read()  # raw output is sanitized

    fake_collector["findings"] = [mk("B", 1), mk("C", 2)]
    run_audit(cfg, no_ai=True)
    run = json.load(open(f"{latest}/run.json"))
    fs = json.load(open(f"{latest}/findings.json"))
    assert run["new_count"] == 1 and [r["id"] for r in run["resolved"]] == ["A"]
    assert next(f for f in fs if f["id"] == "C")["new"]
    assert "Resolvido: fake/A" in open(f"{latest}/report.md").read()
    assert len(os.listdir(f"{cfg['state_dir']}/history")) == 2


def test_history_is_pruned(cfg, fake_collector, monkeypatch):
    monkeypatch.setenv("PAWDIT_ALLOW_USER", "1")
    cfg.update(tools=["fake"], history_keep=2)
    for _ in range(4):
        run_audit(cfg, no_ai=True)
    assert len(os.listdir(f"{cfg['state_dir']}/history")) == 2


def test_run_requires_root(cfg, monkeypatch):
    monkeypatch.delenv("PAWDIT_ALLOW_USER", raising=False)
    monkeypatch.setattr(os, "geteuid", lambda: 1000)
    with pytest.raises(SystemExit):
        run_audit(cfg, no_ai=True)
