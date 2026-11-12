"""Collectors turn a tool's output into normalized findings.

Contract: ``collect(cfg, ctx) -> (findings, meta, raw_text) | None``
``None`` means "tool not available here"; exceptions are caught by the runner and reported as an error.
Parsing lives in separate ``parse_*`` functions so it can be tested without the tool installed.
"""

from __future__ import annotations

from . import aide, auditd, builtin, chkrootkit, lynis, ssh_audit, trivy, vulnix

COLLECTORS = {
    "builtin": builtin.collect,
    "lynis": lynis.collect,
    "ssh-audit": ssh_audit.collect,
    "aide": aide.collect,
    "chkrootkit": chkrootkit.collect,
    "vulnix": vulnix.collect,
    "trivy": trivy.collect,
    "auditd": auditd.collect,
}
