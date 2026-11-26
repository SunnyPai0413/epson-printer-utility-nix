# Upstream source

The input is the locally supplied `epson-printer-utility-1.1.3-1.src.rpm` from Seiko Epson Corporation.
Its RPM spec identifies Epson Printer Utility 1.1.3 and epson-backend 1.3.1, with upstream:
<https://download.ebz.epson.net/dsc/search/01/search/?OSC=LX>.
The original download URL/date were not supplied and are not inferred here.

`rpm/epson-printer-utility.tar.gz`, `rpm/epson-backend.tar.gz`, and the RPM spec were extracted unchanged from that source RPM.
The Nix builds use these exact tarballs and apply `patches/adapt.py` in the sandbox; they do not use upstream binary executables or libraries.
Original licenses, notices, authors and sources remain in the archives. COPYING files are also copied to `LICENSES/` and installed with the packages.
The utility states LGPL-2.1-or-later; the backend states GPL-2.0-or-later with exceptions in individual files. Consult the original file notices for bundled components.
New CLI/build adaptations are GPL-2.0-or-later (see the top-level `LICENSE` and `NOTICE.md`).
Project version is tracked separately in `VERSION`; the retained upstream versions are unchanged.
`SHA256SUMS` also covers the extracted spec. Run `sha256sum -c upstream/SHA256SUMS` from the repository root.
The flake source-integrity check verifies all four retained files.

SHA-256:

```
c2447e3704c1a1af9c9c725823acb778d0f4486425c392673e08a7501ac0124c  epson-printer-utility-1.1.3-1.src.rpm
306afe2cf9bff7fc5996e91ff10e6d86262d6cc6c25e5610f90c51955c720e2e  rpm/epson-backend.tar.gz
2b2031dcd5c3dd4c72089337f60d1b6ef4484850cbaba8a039afdac7ae1982a2  rpm/epson-printer-utility.tar.gz
```
