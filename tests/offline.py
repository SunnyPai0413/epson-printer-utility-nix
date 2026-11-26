# SPDX-License-Identifier: GPL-2.0-or-later
"""No hardware: invalid CLI calls and unavailable printers must fail closed."""
import json
import subprocess
import sys
exe = sys.argv[1]
for command in ['power-ink-flushing', 'reset', 'clean', 'arbitrary-command']:
    p = subprocess.run([exe, command], capture_output=True, text=True)
    assert p.returncode == 2, (command, p.returncode, p.stdout, p.stderr)
for scope in ['usb', 'network']:
    p = subprocess.run([exe, 'ink', '--connection', scope, '--json'], capture_output=True, text=True, timeout=30)
    r = json.loads(p.stdout)
    assert p.returncode == 3 and r['outcome'] == 'unavailable', r
    assert r['schema_version'] == 2 and r['ink'] == [], r
p = subprocess.run([exe, 'nozzle-check', '--connection', 'usb', '--scheduled', '--json'], capture_output=True, text=True, timeout=20)
r = json.loads(p.stdout)
assert p.returncode == 0 and r['outcome'] == 'skipped', r
p = subprocess.run([exe, 'devices', '--connection', 'network', '--json'], capture_output=True, text=True, timeout=30)
r = json.loads(p.stdout)
assert p.returncode == 0 and r['devices'] == [], r
