#!/usr/bin/env bash
# Generic installer (Debian/Ubuntu/Fedora/Bazzite...). On NixOS use contrib/nixos/pawdit.nix.
#   sudo ./install.sh              install or upgrade (idempotent)
#   sudo ./install.sh --uninstall  remove program and units (keeps /etc/pawdit.toml and /var/lib/pawdit)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
PREFIX=/opt/pawdit

if [[ ${1:-} == --uninstall ]]; then
  systemctl disable --now pawdit.timer 2>/dev/null || true
  rm -f /etc/systemd/system/pawdit.service /etc/systemd/system/pawdit.timer /usr/local/bin/pawdit
  rm -rf "$PREFIX"
  systemctl daemon-reload
  echo "removed. kept: /etc/pawdit.toml and /var/lib/pawdit"
  exit 0
fi

python3 -m venv "$PREFIX" || { echo "python3 -m venv failed (Debian/Ubuntu: apt install python3-venv)" >&2; exit 1; }
"$PREFIX/bin/pip" install --quiet --upgrade .
ln -sf "$PREFIX/bin/pawdit" /usr/local/bin/pawdit
[[ -f /etc/pawdit.toml ]] || install -Dm644 contrib/pawdit.toml.example /etc/pawdit.toml
install -Dm644 contrib/systemd/pawdit.service contrib/systemd/pawdit.timer -t /etc/systemd/system/
install -d -m750 /var/lib/pawdit
systemctl daemon-reload
systemctl enable --now pawdit.timer

echo "ok. next: pawdit doctor   then: sudo pawdit run"
