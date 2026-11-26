# SPDX-License-Identifier: GPL-2.0-or-later
"""Run the actual native CUPS backend against a temporary FIFO, never USB."""
import os
import pathlib
import subprocess
import sys
import threading
import fcntl
import time
exe, fixture, directory = sys.argv[1:]
r = subprocess.run([exe, '--version'], capture_output=True, text=True, timeout=5)
assert r.returncode == 0 and '1.3.1' in r.stderr, r
root = pathlib.Path(directory)
root.mkdir(exist_ok=True)
if (root / "ecblp0").exists():
    (root / "ecblp0").unlink()
fifo = root / 'ecblp0'
os.mkfifo(fifo, 0o660)
for name in ['operation.lock', 'fifo.lock']:
    (root / name).touch(mode=0o660)
r = subprocess.run([fixture], capture_output=True, text=True, timeout=5)
assert r.returncode == 0 and 'direct ecblp:' + str(fifo) in r.stdout, r
received = []
def reader():
    with fifo.open('rb') as pipe:
        received.append(pipe.read())
payload = b'Native CUPS data fixture\n' * 4096
job = root / 'print-data'
job.write_bytes(payload)
lock = (root / 'operation.lock').open('r+')
fcntl.flock(lock, fcntl.LOCK_EX)
worker = threading.Thread(target=reader)
worker.start()
child = subprocess.Popen([fixture, '1', 'fixture-user', 'fixture-title', '1', '', str(job)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(0.15)
assert child.poll() is None, 'CUPS must wait for the maintenance lock'
fcntl.flock(lock, fcntl.LOCK_UN)
stdout, stderr = child.communicate(timeout=10)
worker.join(timeout=5)
assert child.returncode == 0 and received == [payload], (child.returncode, stderr, len(received))
# No active reader: finite failure; never claim a successful job.
r = subprocess.run([fixture, '2', 'fixture-user', 'fixture-title', '1', '', str(job)], capture_output=True, timeout=10)
assert r.returncode != 0, r

# A reader disappearing after a prefix is a reported failure, not SIGPIPE/success.
def broken_reader():
    with fifo.open('rb', buffering=0) as pipe:
        pipe.read(1)
worker = threading.Thread(target=broken_reader)
worker.start()
r = subprocess.run([fixture, '3', 'fixture-user', 'fixture-title', '1', '', str(job)], capture_output=True, timeout=10)
worker.join(timeout=5)
assert r.returncode == 1, (r.returncode, r.stderr)
