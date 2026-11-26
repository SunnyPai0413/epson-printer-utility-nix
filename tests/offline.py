"""No hardware or mock protocol: offline CLI must fail closed, never claim success."""
import json
import subprocess
import sys
exe = sys.argv[1]
for command in ['power-ink-flushing', 'reset', 'clean']:
    p = subprocess.run([exe, command], capture_output=True, text=True)
    assert p.returncode == 2, (command, p.returncode, p.stdout, p.stderr)
p = subprocess.run([exe, 'ink', '--json'], capture_output=True, text=True, timeout=15)
r = json.loads(p.stdout)
assert p.returncode == 3 and r['outcome'] == 'unavailable', r
assert len(r['ink']) == 6 and all(row['reported_percent'] is None for row in r['ink']), r
p = subprocess.run([exe, 'nozzle-check', '--scheduled', '--json'], capture_output=True, text=True, timeout=15)
r = json.loads(p.stdout)
assert p.returncode == 0 and r['outcome'] == 'skipped', r
