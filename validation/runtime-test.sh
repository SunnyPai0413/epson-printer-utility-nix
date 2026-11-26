#!/usr/bin/env bash
# Temporary validation only. No /etc changes or NixOS activation.
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
action=${1:-help}
if [[ $action == help ]]; then
  printf '%s\n' 'As root: runtime-test.sh start <USB-serial> <product-id> <operator-name>' \
    'As root: runtime-test.sh nozzle-check' 'As root: runtime-test.sh stop' \
    'start/stop only manage a temporary backend; nozzle-check submits exactly one native pattern.'
  exit 0
fi
[[ $EUID == 0 ]] || { echo 'Run with sudo or pkexec; never pass a password in arguments.' >&2; exit 1; }
backend=$(readlink -f "$project/result-backend")
utility=$(readlink -f "$project/result-utility")
case "$action" in
 start)
  [[ $# == 4 ]] || exit 2
  serial=$2; product=$3; operator=$4
  [[ $product =~ ^[[:xdigit:]]{4}$ ]] || exit 2
  group=$(id -g "$operator")
  if systemctl is-active --quiet ecbd; then echo 'ecbd already active; use its installed module instead'; exit 1; fi
  install -d -m 0770 -o root -g "$group" /run/epson-printer-utility
  touch /run/epson-printer-utility/operation.lock
  chown root:"$group" /run/epson-printer-utility/operation.lock
  chmod 0660 /run/epson-printer-utility/operation.lock
  systemd-run --unit=epson-ecbd-validation --property=Type=simple \
    --property=Group="$group" --property=UMask=0007 --property=TimeoutStopSec=10 \
    --setenv=EPSON_USB_SERIAL="$serial" --setenv=EPSON_USB_PRODUCT="$product" \
    "$backend/bin/ecbd"
  ;;
 nozzle-check)
  # Same CLI and options as nixosModules.default's timer service. No timer is enabled.
  systemd-run --unit=epson-nozzle-check --property=Type=oneshot \
    --property=TimeoutStartSec=150 --property=Restart=no \
    "$utility/bin/epson-printer-cli" nozzle-check --scheduled --json --device auto
  ;;
 stop)
  systemctl stop epson-ecbd-validation.service
  # The stopped root test daemon must not leave a root-owned PID file for the module's user.
  rm -f /run/epson-printer-utility/ecbd.pid
  # Never unlink the shared operation lock; it may still be held by a client.
  ;;
 *) exit 2 ;;
esac
