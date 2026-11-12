import json
from pathlib import Path

from pawdit.collectors.aide import parse_aide
from pawdit.collectors.lynis import parse_lynis
from pawdit.collectors.ssh_audit import parse_ssh_audit
from pawdit.collectors.trivy import parse_trivy
from pawdit.collectors.vulnix import parse_vulnix

FIX = Path(__file__).parent / "fixtures"


def test_lynis_real_report():
    fs, meta = parse_lynis((FIX / "lynis-report.dat").read_text())
    assert meta["score"] == 61
    assert len(fs) == 13
    warn = next(f for f in fs if f["id"] == "PKGS-7392")
    assert warn["sev"] == 3 and warn["hint"] == "" and warn["detail"] == ""
    # same id with different text must be two distinct findings (distinct keys)
    auth = [f for f in fs if f["id"] == "AUTH-9286"]
    assert len(auth) == 2 and auth[0]["key"] != auth[1]["key"]
    assert next(f for f in fs if f["id"] == "AUTH-9230")["sev"] == 2  # AUTH is a boosted prefix
    assert next(f for f in fs if f["id"] == "BOOT-5180")["sev"] == 1


def test_lynis_keys_are_stable_across_runs():
    text = (FIX / "lynis-report.dat").read_text()
    assert [f["key"] for f in parse_lynis(text)[0]] == [f["key"] for f in parse_lynis(text)[0]]


SSH = """(gen) software: OpenSSH 9.6
(kex) curve25519-sha256 -- [info] available since OpenSSH 7.4
(kex) diffie-hellman-group14-sha1 -- [fail] using broken SHA-1 hash algorithm
(kex) ecdh-sha2-nistp256 -- [warn] using weak elliptic curves
(mac) hmac-sha1 -- [fail] using broken SHA-1 hash algorithm
(rec) -diffie-hellman-group14-sha1 -- kex algorithm to remove
(rec) -hmac-sha1 -- mac algorithm to remove"""


def test_ssh_audit_groups_by_level():
    fs = parse_ssh_audit(SSH)
    fail = next(f for f in fs if f["id"] == "SSH-FAIL")
    assert fail["sev"] == 3 and "2 algoritmos" in fail["title"] and "hmac-sha1" in fail["hint"]
    assert next(f for f in fs if f["id"] == "SSH-WARN")["sev"] == 2


AIDE = """Summary:
  Total number of entries:	1234
  Added entries:		1
  Removed entries:		0
  Changed entries:		2

Added entries:
---------------------------------------------------
f++++++++++++++++: /etc/novo.conf

Changed entries:
---------------------------------------------------
f   ...    .C... : /etc/hosts
d =.... mc.. .. . : /etc

Detailed information about changes:
---------------------------------------------------
File: /etc/hosts
"""


def test_aide_counts_and_paths():
    fs = {f["id"]: f for f in parse_aide(AIDE)}
    assert set(fs) == {"AIDE-ADDED", "AIDE-CHANGED"}  # removed=0 -> no finding
    assert fs["AIDE-ADDED"]["detail"] == "/etc/novo.conf"
    assert fs["AIDE-CHANGED"]["detail"] == "/etc/hosts, /etc"  # no duplicates from the "Detailed" section
    assert fs["AIDE-CHANGED"]["sev"] == 3


def test_vulnix_skips_whitelisted_and_ranks_by_cvss():
    data = [
        {"name": "zlib-1.3", "pname": "zlib", "affected_by": ["CVE-9"], "whitelisted": ["CVE-9"]},
        {
            "name": "openssl-3.0.1",
            "pname": "openssl",
            "affected_by": ["CVE-1", "CVE-2"],
            "whitelisted": [],
            "cvssv3_basescore": {"CVE-1": 9.8, "CVE-2": 5.0},
        },
        {
            "name": "curl-8",
            "pname": "curl",
            "affected_by": ["CVE-3"],
            "whitelisted": [],
            "cvssv3_basescore": {"CVE-3": 4.3},
        },
    ]
    fs = parse_vulnix(json.dumps(data))
    assert [f["id"] for f in fs] == ["NIX-openssl", "NIX-curl"]
    assert fs[0]["sev"] == 4 and fs[1]["sev"] == 2


def test_vulnix_caps_and_aggregates_the_rest():
    data = [
        {"name": f"p{i}-1", "pname": f"p{i}", "affected_by": [f"CVE-{i}"], "cvssv3_basescore": {f"CVE-{i}": 5.0}}
        for i in range(20)
    ]
    fs = parse_vulnix(json.dumps(data), top=5)
    assert len(fs) == 6 and fs[-1]["id"] == "NIX-OUTROS"


def test_vulnix_garbage_input_is_not_fatal():
    assert parse_vulnix("not json") == []


def test_trivy_groups_by_package_and_suggests_fixed_version():
    data = {
        "Results": [
            {
                "Vulnerabilities": [
                    {"PkgName": "openssl", "VulnerabilityID": "CVE-1", "Severity": "HIGH", "FixedVersion": "3.0.2"},
                    {"PkgName": "openssl", "VulnerabilityID": "CVE-2", "Severity": "LOW"},
                    {"PkgName": "bash", "VulnerabilityID": "CVE-3", "Severity": "CRITICAL", "FixedVersion": "5.2"},
                ]
            }
        ]
    }
    fs = parse_trivy(json.dumps(data))
    assert [f["id"] for f in fs] == ["PKG-bash", "PKG-openssl"]
    assert fs[0]["hint"] == "atualize bash para 5.2" and fs[0]["sev"] == 4
