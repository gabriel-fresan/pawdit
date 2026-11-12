"""Docker parsers. Fixtures are hand-written (synthetic) from the documented `docker inspect` schema."""

import json
import stat

from pawdit.collectors.docker import parse_containers, parse_daemon, parse_image

SAFE = {
    "Name": "/web",
    "Config": {"Image": "nginx:1.27", "User": "101"},
    "HostConfig": {},
    "Mounts": [],
    "NetworkSettings": {"Ports": {"80/tcp": [{"HostIp": "127.0.0.1", "HostPort": "80"}]}},
}
BAD = {
    "Name": "/agent",
    "Config": {"Image": "ci/runner:latest"},
    "HostConfig": {
        "Privileged": True,
        "PidMode": "host",
        "NetworkMode": "host",
        "CapAdd": ["CAP_SYS_ADMIN", "NET_ADMIN"],
        "SecurityOpt": ["seccomp=unconfined"],
    },
    "Mounts": [{"Source": "/var/run/docker.sock", "RW": True}, {"Source": "/etc", "RW": False}],
    "NetworkSettings": {"Ports": {"8080/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]}},
}


def by_id(fs):
    return {f["id"]: f for f in fs}


def test_safe_container_is_clean():
    assert parse_containers([SAFE]) == []


def test_dangerous_container():
    d = by_id(parse_containers([SAFE, BAD]))
    assert d["CT-PRIV-agent"]["sev"] == 4
    assert d["CT-SOCK-agent"]["sev"] == 4
    assert d["CT-CAP-agent"]["sev"] == 3
    assert d["CT-PID-agent"]["sev"] == 3
    assert d["CT-SEC-agent"]["sev"] == 2
    assert d["CT-MNT_etc-agent"]["sev"] == 1  # read-only sensitive mount
    assert d["CT-LATEST"]["detail"] == "agent" and d["CT-PORTS"]["detail"] == "agent"
    assert "CT-ROOT" not in d  # privileged container is reported on its own, web runs as 101


def test_ids_are_stable():
    assert [f["key"] for f in parse_containers([BAD])] == [f["key"] for f in parse_containers([BAD])]


def test_daemon():
    d = by_id(
        parse_daemon(
            {"/run/docker.sock": stat.S_IFSOCK | 0o666},
            ["gabriel"],
            {"hosts": ["tcp://0.0.0.0:2375"]},
            {"SecurityOptions": ["name=seccomp"]},
        )
    )
    assert d["SOCK-PERM"]["sev"] == 4 and d["TCP-NOTLS"]["sev"] == 4 and d["GROUP"]["sev"] == 1 and "NO-USERNS" in d
    ok = parse_daemon({"/run/docker.sock": stat.S_IFSOCK | 0o660}, [], {}, {"SecurityOptions": ["name=rootless"]})
    assert ok == []


def test_image_cves():
    out = json.dumps(
        {
            "Results": [
                {
                    "Vulnerabilities": [
                        {"VulnerabilityID": "CVE-1", "PkgName": "openssl", "Severity": "CRITICAL"},
                        {"VulnerabilityID": "CVE-2", "PkgName": "zlib", "Severity": "LOW"},
                        {"VulnerabilityID": "CVE-3", "PkgName": "curl", "Severity": "HIGH"},
                    ]
                }
            ]
        }
    )
    [f] = parse_image(out, "nginx:1.20")
    assert f["sev"] == 4 and "CVE-1" in f["detail"] and "CVE-2" not in f["detail"] and "2 CVEs" in f["title"]
    assert parse_image("{}", "x") == [] and parse_image("lixo", "x") == []
