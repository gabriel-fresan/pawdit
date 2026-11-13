"""Command-line entry point."""

from __future__ import annotations

import argparse
import signal
import sys

from . import commands, util
from .config import load_cfg


class _Help(argparse.Action):
    """-h/--help at the top level prints the coloured overview instead of argparse's plain usage."""

    def __init__(self, option_strings, dest, **kw):
        super().__init__(option_strings, dest, nargs=0, default=argparse.SUPPRESS, help="mostra esta ajuda")

    def __call__(self, parser, namespace, values, option_string=None):
        show_help()
        parser.exit()


# (grupo, [(comando, descrição)]) — a ordem é a do `pawdit help`
HELP = [
    (
        "ver  (sem sudo, para quem está no grupo admin)",
        [
            ("pawdit", "resumo curto — o mesmo do login SSH"),
            ("report", "relatório completo, renderizado no terminal"),
            ("list [--new] [--min-sev N]", "todos os achados, do mais grave ao menos"),
            ("fix", "visão geral das soluções sugeridas pela IA"),
            ("fix N|ID [--gen]", "solução completa de um achado (--gen gera o texto agora)"),
            ("diff", "o que apareceu e o que foi resolvido"),
            ("history [-n N]", "evolução semanal: score e contagens"),
            ("raw [ferramenta]", "saída bruta de uma ferramenta"),
        ],
    ),
    (
        "rodar",
        [
            ("sudo pawdit run [--no-ai] [--only a,b]", "auditoria agora (o timer faz isso toda semana)"),
            ("pawdit ai [--model M] [--max N]", "regera os textos de IA da última auditoria"),
        ],
    ),
    (
        "outros",
        [("doctor", "checa ferramentas, Ollama e permissões"), ("help [comando]", "esta ajuda (ou a de um comando)")],
    ),
]
EXAMPLES = [
    "pawdit fix 3                 # como corrigir o achado #3",
    "pawdit list --min-sev 3      # só altos e críticos",
    "sudo pawdit run --only lynis,docker --no-ai",
    "pawdit report | less -R      # force cor em pipe: FORCE_COLOR=1",
]


def show_help(topic=None, parser=None):
    from . import __version__, faces
    from .util import paint

    if topic and parser:
        sub = next((a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None)
        if sub and topic in sub.choices:
            sub.choices[topic].print_help()
            return
        print(f"pawdit: comando '{topic}' não existe\n", file=sys.stderr)
    print(
        faces.banner("ok", f"pawdit {__version__}") + paint("2", "  auditoria semanal + resumo por LLM pequeno local")
    )
    for title, rows in HELP:
        print("\n" + paint("1;36", title))
        w = max(len(c) for c, _ in rows)
        for cmd, desc in rows:
            print("  " + paint("1", cmd.ljust(w)) + "  " + paint("2", desc))
    print("\n" + paint("1;36", "exemplos"))
    for ex in EXAMPLES:
        print("  " + paint("38;5;180", ex))
    print("\n" + paint("2", "cada comando aceita -h (ex.: pawdit fix -h) · NO_COLOR desliga as cores"))


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="pawdit", description="auditoria semanal + resumo por LLM pequeno local", add_help=False
    )
    ap.add_argument("-h", "--help", action=_Help)
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
    p = sub.add_parser("fix", help="solução recomendada (sem argumento: visão geral de todas)")
    p.add_argument("ref", nargs="?", help="número ou id do achado")
    p.add_argument("--gen", action="store_true", help="gera o texto agora, se ainda não existir")
    p.add_argument("--max", type=int, help="visão geral: quantos achados (padrão 20)")
    sub.add_parser("diff", help="o que mudou desde a última")
    p = sub.add_parser("history", help="evolução semanal")
    p.add_argument("-n", type=int, default=12)
    p = sub.add_parser("raw", help="saída bruta de uma ferramenta")
    p.add_argument("tool", nargs="?")
    sub.add_parser("doctor", help="checa ferramentas, Ollama e permissões")
    p = sub.add_parser("help", help="ajuda geral ou de um comando")
    p.add_argument("topic", nargs="?", help="comando")
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
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.cmd == "help":
        show_help(a.topic, ap)
        return 0
    cfg = load_cfg()
    if a.cmd is None:  # bare `pawdit` behaves like `pawdit greet`
        a = argparse.Namespace(force=False)
        commands.cmd_greet(cfg, a)
    else:
        COMMANDS[a.cmd](cfg, a)
    return 0
