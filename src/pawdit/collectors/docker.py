"""Docker / Podman checks: running-container configuration, daemon exposure and image CVEs (via trivy)."""

from __future__ import annotations

import json
import os
import shutil
import stat

from ..models import F
from ..util import one_line, sh

BAD_CAPS = {
    "SYS_ADMIN": 3,
    "ALL": 3,
    "SYS_MODULE": 3,
    "SYS_PTRACE": 2,
    "SYS_RAWIO": 3,
    "DAC_READ_SEARCH": 2,
    "NET_ADMIN": 1,
}
SENSITIVE_MOUNTS = {"/": 4, "/etc": 3, "/root": 3, "/boot": 3, "/proc": 3, "/sys": 2, "/dev": 3, "/var/lib/docker": 3}
SOCKETS = ("/var/run/docker.sock", "/run/docker.sock", "/run/podman/podman.sock", "/var/run/podman/podman.sock")
_TRIVY_SEV = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def _name(c):
    return (c.get("Name") or c.get("Id", "?")[:12]).lstrip("/")


def parse_containers(items):
    """``docker inspect`` JSON (list) -> findings. Per-container for dangerous setups, aggregated for low-noise ones."""
    fs, roots, latest, exposed = [], [], [], []
    for c in items:
        n = _name(c)
        hc = c.get("HostConfig") or {}
        cfg = c.get("Config") or {}

        def add(kind, title, sev, detail="", hint="", n=n):
            fs.append(F("docker", f"CT-{kind}-{n}", f"container {n}: {title}", sev, detail, hint))

        if hc.get("Privileged"):
            add(
                "PRIV",
                "roda com --privileged (acesso total ao host)",
                4,
                "",
                "remova --privileged; use cap_add só do necessário",
            )
        for m in c.get("Mounts") or []:
            src = (m.get("Source") or "").rstrip("/") or "/"
            if src.endswith("docker.sock") or src.endswith("podman.sock"):
                add(
                    "SOCK",
                    f"monta {src} (controle do daemon = root no host)",
                    4,
                    "",
                    "evite montar o socket; use um proxy restrito (ex.: docker-socket-proxy)",
                )
            elif src in SENSITIVE_MOUNTS:
                rw = m.get("RW", True)
                add(
                    f"MNT{src.replace('/', '_')}",
                    f"monta {src} do host" + (" com escrita" if rw else " (somente leitura)"),
                    SENSITIVE_MOUNTS[src] if rw else 1,
                    "",
                    "monte só o subdiretório necessário e como :ro",
                )
        if hc.get("NetworkMode") == "host":
            add(
                "NET",
                "usa a rede do host (--network host)",
                2,
                "",
                "use uma rede bridge e publique só as portas necessárias",
            )
        if hc.get("PidMode") == "host":
            add("PID", "compartilha o namespace de PID do host", 3, "", "remova --pid=host")
        if hc.get("IpcMode") == "host":
            add("IPC", "compartilha o IPC do host", 3, "", "remova --ipc=host")
        caps = [x.removeprefix("CAP_") for x in (hc.get("CapAdd") or [])]
        bad = {x: BAD_CAPS[x] for x in caps if x in BAD_CAPS}
        if bad:
            add(
                "CAP",
                "capabilities perigosas: " + ", ".join(sorted(bad)),
                max(bad.values()),
                "",
                "use cap_drop: ALL e adicione só o necessário",
            )
        sec = [s.replace(":", "=") for s in (hc.get("SecurityOpt") or [])]
        if any("unconfined" in s for s in sec):
            add("SEC", "seccomp/apparmor desativado (unconfined)", 2, ", ".join(sec), "remova security_opt unconfined")
        if (cfg.get("User") or "") in ("", "0", "root", "0:0") and not hc.get("Privileged"):
            roots.append(n)
        image = cfg.get("Image") or ""
        if image and (":" not in image.rsplit("/", 1)[-1] or image.endswith(":latest")):
            latest.append(n)
        for binds in ((c.get("NetworkSettings") or {}).get("Ports") or {}).values():
            if any(b.get("HostIp") in ("0.0.0.0", "", "::") for b in binds or []):
                exposed.append(n)
                break
    if roots:
        fs.append(
            F(
                "docker",
                "CT-ROOT",
                f"{len(roots)} container(s) rodando como root",
                1,
                ", ".join(roots[:8]),
                "defina USER não-root na imagem ou user: no compose",
            )
        )
    if latest:
        fs.append(
            F(
                "docker",
                "CT-LATEST",
                f"{len(latest)} container(s) com imagem :latest/sem tag",
                1,
                ", ".join(latest[:8]),
                "fixe a versão (ou digest) para atualizar de forma controlada",
            )
        )
    if exposed:
        fs.append(
            F(
                "docker",
                "CT-PORTS",
                f"{len(exposed)} container(s) publicam portas em todas as interfaces",
                1,
                ", ".join(exposed[:8]),
                "publique em 127.0.0.1:porta:porta se não precisa de acesso externo",
            )
        )
    return fs


def parse_daemon(sock_modes, group_members, daemon_json, info=None):
    """Daemon exposure: socket permissions, docker group, TCP without TLS, rootless/userns."""
    fs = []
    for path, mode in sock_modes.items():
        if mode & stat.S_IWOTH:
            fs.append(
                F(
                    "docker",
                    "SOCK-PERM",
                    f"{path} gravável por qualquer usuário",
                    4,
                    oct(mode & 0o7777),
                    "chmod 660 e grupo docker",
                )
            )
    if group_members:
        fs.append(
            F(
                "docker",
                "GROUP",
                f"grupo docker tem {len(group_members)} membro(s) (equivale a root)",
                1,
                ", ".join(group_members),
                "restrinja o grupo ou use docker rootless",
            )
        )
    hosts = (daemon_json or {}).get("hosts") or []
    if any(str(h).startswith("tcp://") for h in hosts) and not (daemon_json or {}).get("tlsverify"):
        fs.append(
            F(
                "docker",
                "TCP-NOTLS",
                "daemon escuta em TCP sem tlsverify",
                4,
                ", ".join(map(str, hosts)),
                "remova tcp:// ou habilite tlsverify com certificados",
            )
        )
    sec = " ".join((info or {}).get("SecurityOptions") or [])
    if info and "rootless" not in sec and "userns" not in sec and not (daemon_json or {}).get("userns-remap"):
        fs.append(
            F(
                "docker",
                "NO-USERNS",
                "daemon roda como root sem userns-remap/rootless",
                1,
                "",
                "considere docker rootless ou userns-remap",
            )
        )
    return fs


def parse_image(txt, image, top=6):
    try:
        data = json.loads(txt)
    except ValueError:
        return []
    vs = [v for r in data.get("Results") or [] for v in r.get("Vulnerabilities") or []]
    vs = [v for v in vs if _TRIVY_SEV.get(v.get("Severity", ""), 0) >= 2]
    if not vs:
        return []
    sev = max(_TRIVY_SEV[v["Severity"]] for v in vs)
    worst = sorted(vs, key=lambda v: -_TRIVY_SEV[v["Severity"]])[:top]
    pk = sorted({v.get("PkgName", "?") for v in worst})
    return [
        F(
            "docker-images",
            f"IMG-{image}",
            f"imagem {image}: {len(vs)} CVEs corrigíveis (médio+)",
            sev,
            ", ".join(v.get("VulnerabilityID", "?") for v in worst) + " · pacotes: " + ", ".join(pk),
            "docker pull / rebuild da imagem base e recrie o container",
        )
    ]


def _runtime():
    for exe in ("docker", "podman"):
        p = shutil.which(exe)
        if p:
            return p
    return None


def _running(exe):
    rc, out, _ = sh([exe, "ps", "-q"], 30)
    ids = out.split() if rc == 0 else None
    if not ids:
        return [] if ids is not None else None
    rc, out, err = sh([exe, "inspect", *ids], 60)
    if rc != 0:
        raise RuntimeError(one_line(err, 200) or f"inspect rc={rc}")
    return json.loads(out)


def collect(cfg, ctx):
    exe = _runtime()
    if not exe:
        return None
    items = _running(exe)
    if items is None:  # daemon not running / no access: nothing to audit here
        return None
    fs = parse_containers(items)
    modes = {}
    for s in SOCKETS:
        try:
            modes[s] = os.stat(s).st_mode
        except OSError:
            pass
    members = []
    try:
        import grp

        members = [m for m in grp.getgrnam("docker").gr_mem]
    except (ImportError, KeyError):
        pass
    daemon = {}
    try:
        with open("/etc/docker/daemon.json", encoding="utf-8") as fh:
            daemon = json.load(fh)
    except (OSError, ValueError):
        pass
    info = {}
    if os.path.basename(exe) == "docker":
        rc, out, _ = sh([exe, "info", "--format", "{{json .}}"], 30)
        if rc == 0:
            try:
                info = json.loads(out)
            except ValueError:
                pass
    fs += parse_daemon(modes, members, daemon, info or None)
    return (
        fs,
        {"containers": len(items)},
        json.dumps([{"name": _name(c), "image": (c.get("Config") or {}).get("Image")} for c in items], indent=1),
    )


def collect_images(cfg, ctx):
    exe, trivy = _runtime(), shutil.which("trivy")
    if not exe or not trivy:
        return None
    rc, out, _ = sh([exe, "ps", "--format", "{{.Image}}"], 30)
    if rc != 0:
        return None
    images = sorted(set(out.split()))[: cfg.get("docker_max_images", 8)]
    fs, raw = [], []
    for img in images:
        rc, o, err = sh(
            [trivy, "image", "--quiet", "--format", "json", "--scanners", "vuln", "--ignore-unfixed", img],
            cfg["tool_timeout"],
        )
        if rc != 0:
            raw.append(f"# {img}: erro {one_line(err, 150)}")
            continue
        raw.append(f"# {img}: ok")
        fs += parse_image(o, img)
    if not images:
        return None
    return fs, {"images": len(images)}, "\n".join(raw)
