# 0.2.0 release notes — draft, not published

Independent community Nix Flake for Epson's native Linux utility. This project is
not affiliated with or endorsed by Seiko Epson Corporation.

Upstream remains **Printer Utility 1.1.3 / epson-backend 1.3.1**. Project version
0.2.0 adds packaging and adaptations; it is not an upstream upgrade.

- Restore EPSCommonLib network discovery, connection and maintenance paths, including
  network-only NixOS installations without ecbd or USB permissions.
- Share detailed USB/public status and warning mappings, reported color lists and
  original IDs, unknown ink handling and native paper feed counters across GUI/CLI.
- Keep `status`, `ink`, `nozzle-check`, `clean`; add `devices`, `paper-count` and
  native-ID/address selection. **JSON schema 2 is a compatibility change**: see
  [JSON.md](JSON.md), especially variable ink lists and distinct black variants.
- Build/install ecblp, optionally integrate it through `services.printing.drivers`,
  and coordinate USB FIFO writers and maintenance without stopping CUPS. No queue
  creation/migration is performed; a suitable model driver is still required.
- Move GUI maintenance waiting into a worker. Scheduling remains off by default;
  offline/busy/locked runs skip, with no catch-up, replay or automatic cleaning.
- Preserve original source RPM/tarballs, checksums, file notices and third-party
  licenses. New code is GPL-2.0-or-later. Modified upstream files carry dated modification
  notices, and the packages include a generated list of adapted files.

Validation: see [the dated validation record](../validation/README.md) for the
actual build/check and hardware results. Existing L805 USB evidence is retained. The new L805 read-only regression passed
enumeration, status, actual ink/unknown values, native feed counters and ecblp
discovery; the new GUI launched in a real desktop. CUPS stayed active and the
temporary backend was stopped afterward.
No cleaning is repeated for release. Network hardware, other models, actual CUPS
printing/coexistence, full NixOS module activation and aarch64 builds remain
unverified. No all-model compatibility claim is made.

Before publishing this draft, use the final validation record and review the
working tree. This document remains a draft; publishing source changes does not create a tag
or GitHub Release.
