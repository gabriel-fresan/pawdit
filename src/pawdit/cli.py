"""Command-line entry point."""

from __future__ import annotations

import argparse
import signal
import sys

from . import commands, util
from .config import load_cfg


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="pawdit", description="auditoria semanal + resumo por LLM pequeno local")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("run", help="roda a auditoria agora (root)")
    p.add_argument("--no-ai", action="store_true")
    p.add_argument("--only", help="coletores separados por vírgula")
    p.add_argument("--model")
    p.add_argument("--max", type=int, help="quantos achados recebem texto de IA")
    p = sub.add_parser("ai", help="regera os textos de IA da última auditoria (root)")
    p.add_argument("--model")
    p.add_argument("--max", type=int)
    p = sub.add_parser("greet", help="resumo curto (usado no login SSH)")
    p.add_argument("--force", action="store_true")
    sub.add_parser("report", help="relatório completo")
    p = sub.add_parser("list", help="lista de achados")
    p.add_argument("--new", action="store_true")
    p.add_argument("--min-sev", type=int, choices=[1, 2, 3, 4])
    p = sub.add_parser("fix", help="solução recomendada (sem argumento: menu)")
    p.add_argument("ref", nargs="?", help="número ou id do achado")
    p.add_argument("--gen", action="store_true", help="gera o texto agora, se ainda não existir")
    sub.add_parser("diff", help="o que mudou desde a última")
    p = sub.add_parser("history", help="evolução semanal")
    p.add_argument("-n", type=int, default=12)
    p = sub.add_parser("raw", help="saída bruta de uma ferramenta")
    p.add_argument("tool", nargs="?")
    sub.add_parser("doctor", help="checa ferramentas e Ollama")
    return ap


COMMANDS = {
    "run": commands.cmd_run,
    "ai": commands.cmd_ai,
    "greet": commands.cmd_greet,
    "report": commands.cmd_report,
    "list": commands.cmd_list,
    "fix": commands.cmd_fix,
    "diff": commands.cmd_diff,
    "history": commands.cmd_history,
    "raw": commands.cmd_raw,
    "doctor": commands.cmd_doctor,
}


def main(argv=None) -> int:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # `pawdit list | head` without a traceback
    import os

    util.set_color((sys.stdout.isatty() and "NO_COLOR" not in os.environ) or "FORCE_COLOR" in os.environ)
    a = build_parser().parse_args(argv)
    cfg = load_cfg()
    if a.cmd is None:  # bare `pawdit` behaves like `pawdit greet`
        a = argparse.Namespace(force=False)
        commands.cmd_greet(cfg, a)
    else:
        COMMANDS[a.cmd](cfg, a)
    return 0
