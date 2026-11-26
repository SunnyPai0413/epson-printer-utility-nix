# SPDX-License-Identifier: GPL-2.0-or-later
"""Run the actual native CUPS backend against a temporary FIFO, never USB."""
import os
import pathlib
import errno
import signal
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
# Exceed the default pipe capacity even on Linux with 64 KiB pages.
payload = b'Native CUPS data fixture\n' * 65536
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

# A live reader may stop consuming for longer than the old five-second timeout.
# Resume in small chunks and require byte-exact delivery with no replay.
slow_received = []
def slow_reader(received, ready=None, resume=None):
    with fifo.open('rb', buffering=0) as pipe:
        assert len(payload) > fcntl.fcntl(pipe, fcntl.F_GETPIPE_SZ)
        chunks = [pipe.read(1)]
        if ready is not None:
            ready.set()
        if resume is None:
            time.sleep(6)
        else:
            resume.wait(timeout=10)
        while chunk := pipe.read(1024):
            chunks.append(chunk)
            time.sleep(0.001)
        received.append(b''.join(chunks))
worker = threading.Thread(target=slow_reader, args=(slow_received,))
worker.start()
r = subprocess.run([fixture, 'slow', 'fixture-user', 'fixture-title', '1', '', str(job)], capture_output=True, timeout=15)
worker.join(timeout=5)
assert r.returncode == 0 and slow_received == [payload], (r.returncode, r.stderr, [len(data) for data in slow_received])
assert b'ERROR:' not in r.stderr, r.stderr

# CUPS must still be able to cancel a backpressured file or stdin job.
for from_stdin in (False, True):
    cancelled_received = []
    ready, resume = threading.Event(), threading.Event()
    worker = threading.Thread(target=slow_reader, args=(cancelled_received, ready, resume), daemon=True)
    worker.start()
    args = [fixture, 'cancel', 'fixture-user', 'fixture-title', '1', '']
    if not from_stdin:
        args.append(str(job))
    with job.open('rb') as source:
        child = subprocess.Popen(args, stdin=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            assert ready.wait(timeout=3), 'reader never received a print prefix'
            time.sleep(0.15)
            child.terminate()
            stdout, stderr = child.communicate(timeout=2)
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=2)
            resume.set()
            worker.join(timeout=5)
    assert child.returncode == -signal.SIGTERM, (child.returncode, stderr)
    assert len(cancelled_received) == 1 and 0 < len(cancelled_received[0]) < len(payload), cancelled_received
    assert payload.startswith(cancelled_received[0]), 'cancelled print must not replay data'

# No active reader: finite failure; never claim a successful job.
r = subprocess.run([fixture, '2', 'fixture-user', 'fixture-title', '1', '', str(job)], capture_output=True, timeout=10)
assert r.returncode == 1 and b'stage=fifo-open' in r.stderr, r
assert f'errno={errno.ENXIO} '.encode() in r.stderr, r.stderr

# A reader disappearing after a prefix is a reported failure, not SIGPIPE/success.
def broken_reader():
    with fifo.open('rb', buffering=0) as pipe:
        pipe.read(1)
        time.sleep(0.2)  # Let the writer fill the FIFO and enter poll().
worker = threading.Thread(target=broken_reader)
worker.start()
r = subprocess.run([fixture, '3', 'fixture-user', 'fixture-title', '1', '', str(job)], capture_output=True, timeout=10)
worker.join(timeout=5)
assert r.returncode == 1, (r.returncode, r.stderr)
assert b'stage=poll' in r.stderr and b'poll revents=0x' in r.stderr, r.stderr
assert f'errno={errno.EPIPE} '.encode() in r.stderr and b'reader disconnected' in r.stderr, r.stderr
assert b'not replaying data' in r.stderr, r.stderr
