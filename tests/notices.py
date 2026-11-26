# SPDX-License-Identifier: GPL-2.0-or-later
"""Check all adapted files against the pristine retained source archives."""
from pathlib import Path
import sys
import tarfile

root = Path(sys.argv[1])
changed = set()
prefix = b'/*\n * Modified by the epson-printer-utility-nix project.\n'
for name in ('epson-printer-utility', 'epson-backend'):
    with tarfile.open(root / 'upstream' / 'rpm' / (name + '.tar.gz')) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            path = root / member.name
            assert path.is_file(), member.name
            original = archive.extractfile(member).read()
            adapted = path.read_bytes()
            if adapted != original:
                changed.add(member.name)
                assert adapted.startswith(prefix), member.name
                notice, body = adapted.split(b' */\n', 1)
                assert b'Modification date: 2026-11-26.' in notice, member.name
                assert b'Original copyright, license and exception notices' in notice, member.name
                assert not body.startswith(prefix), 'Duplicate notice: ' + member.name

manifest = (root / 'UPSTREAM-MODIFICATIONS.txt').read_text().splitlines()
listed = {line for line in manifest if line.startswith(('epson-printer-utility/', 'epson-backend/'))}
assert changed and changed == listed, (sorted(changed - listed), sorted(listed - changed))
print(f'Verified dated modification notices for {len(changed)} adapted upstream files.')
