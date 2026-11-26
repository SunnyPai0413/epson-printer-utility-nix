# License and provenance notice

This is an independent community packaging/adaptation project. It is not an Epson
product, is not endorsed or supported by Seiko Epson Corporation, and makes no
claim of compatibility with every Epson printer. Epson names, icons, GUI resources,
and other upstream materials remain the property of their respective owners.

Project version: see `VERSION`. Upstream source versions remain Printer Utility
1.1.3 and epson-backend 1.3.1; project version numbers do not imply an upstream upgrade.

New CLI, Nix/CMake build definitions, adapters and tests in this repository are
licensed under **GPL-2.0-or-later**; the full GPL version 2 text is in `LICENSE`.
Local modifications are identifiable in `patches/adapt.py` and `src/`. They do not
replace the license notices of the upstream files to which they are applied.
During the build, every changed upstream C/C++ file receives a prominent project
modification notice dated 2026-11-26, while retaining the original notices below it.
The generated `UPSTREAM-MODIFICATIONS.txt` lists those files and is installed with
each package. The date describes this adaptation revision; it is fixed in the
adapter for reproducible builds, not taken from the build machine's clock.

The utility archive supplies LGPL-2.1 text, and the backend supplies GPL-2.0 text
with linking exceptions in individual files. Preserve and consult the original
file notices for each component, including bundled ESC/P-R, epsmp, libltdl, IJG/JPEG
related notices and the AVASYS exceptions. Upstream COPYING files are reproduced
unchanged in `LICENSES/`. Original AUTHORS, README, COPYING and all file-level
copyright/third-party notices remain in the unmodified source archives and source
RPM. Bundled libltdl is retained as source and is not linked by this CMake build.
Qt, libusb, libjpeg and other Nix dependencies retain their own licenses.

Sources, extraction details and checksums: [`upstream/SOURCE.md`](upstream/SOURCE.md)
and [`upstream/SHA256SUMS`](upstream/SHA256SUMS). Both packages install their upstream
COPYING/AUTHORS/README and the project license/notice. Distribute the source and
adaptations with any binary release; the archives are part of this repository.
