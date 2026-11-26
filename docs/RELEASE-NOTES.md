# v1.0.0 — first formal public release

Release version: **1.0.0** · Git Tag: **v1.0.0** · Validation date: **2026-11-26**
(Asia/Singapore).

A **NixOS-first** community Flake for Epson's native Linux utility, providing a
Qt GUI, CLI, ecbd USB daemon and optional ecblp CUPS backend. This independent
project is not affiliated with or endorsed by Seiko Epson Corporation.

The retained upstream versions remain **Epson Printer Utility 1.1.3** and
**epson-backend 1.3.1**. Project version 1.0.0 identifies this packaging and
adaptation release, not an Epson upstream upgrade.

## Install and use

With Nix installed and `nix-command` / `flakes` enabled, pin the release Tag:

```sh
nix build github:SunnyPai0413/epson-printer-utility-nix/v1.0.0#default
nix run github:SunnyPai0413/epson-printer-utility-nix/v1.0.0#cli -- --help
nix run github:SunnyPai0413/epson-printer-utility-nix/v1.0.0#gui
```

For NixOS, add this input to your existing system Flake, retain its lock file and
import `inputs.epson-utility.nixosModules.default` in `nixosSystem.modules`:

```nix
inputs.epson-utility.url = "github:SunnyPai0413/epson-printer-utility-nix/v1.0.0";
```

Enable `services.epson-printer-utility`, add your existing user to its `users`
list and rebuild your system. USB is enabled by default. CUPS printing also
requires `cups.enable = true`, a suitable model driver (L805: `pkgs.epson-escpr`)
and a manually configured queue with URI
`ecblp:/run/epson-printer-utility/ecblp0`. The module supplies runtime permissions
and ACLs; it does not create or migrate queues. Follow the
[installation, CLI and CUPS guide](https://github.com/SunnyPai0413/epson-printer-utility-nix/blob/v1.0.0/README.md)
for complete configuration, optional IPP sharing and first-use commands.

Other Linux distributions can use the Nix packages on `x86_64-linux` and
`aarch64-linux`. Native installers and service integration for those distributions
are not supplied; USB services, permissions and CUPS integration require manual
setup. The supported installation guide and hardware evidence are NixOS-focused.

## Included in v1.0.0

- Native USB status/maintenance and EPSCommonLib network discovery/connection
  paths, including a network-only NixOS configuration without ecbd.
- GUI/CLI status and warning mappings, actual reported ink lists and color IDs,
  explicit unknown values, and native paper feed counters. Reported ink values
  are not physical tank measurements; feed counters are not successful page counts.
- CLI `devices`, `status`, `ink`, `paper-count`, `nozzle-check` and `clean`.
  **JSON schema 2 differs from local pre-release clients**; see
  [fields and exit codes](https://github.com/SunnyPai0413/epson-printer-utility-nix/blob/v1.0.0/docs/JSON.md).
  The schema stays at 2 while `project_version` becomes `1.0.0`.
- Optional CUPS integration with shared FIFO and operation locks. ecblp tolerates
  sustained FIFO backpressure while preserving cancellation; disconnected readers
  and I/O errors fail explicitly without replaying print data. Persistent tmpfiles
  ACLs restore CUPS backend access after reboot and cover recreated runtime files.
- GUI maintenance waits in a worker. Scheduled nozzle checks remain off by default;
  offline/busy/locked runs skip without catch-up, replay or automatic cleaning.
- Native x86_64/aarch64 GitHub Actions builds and Cachix binary cache publishing.

## Validation and limits

On **2026-11-26**, the maintainer confirmed **L805 remote IPP multi-page PDF
printing**, with the ecblp FIFO backpressure issue fixed. **Runtime ACLs, CUPS
service and print jobs passed verification after reboot.** The tested path is:

`remote client → IPP → NixOS CUPS → model driver → ecblp/ecbd → USB L805`.

L805 USB enumeration, status, ink/color metadata and native feed counters also
passed the retained read-only regression; earlier nozzle-check/ordinary-clean
evidence is retained. No extra cleaning is performed for release preparation.

Both native CI builds and Cachix uploads succeeded for pre-release baseline
`138ad2f59c20750c66e73173aa0990a27a259335`:
[x86_64-linux](https://github.com/SunnyPai0413/epson-printer-utility-nix/actions/runs/45826063829),
[aarch64-linux](https://github.com/SunnyPai0413/epson-printer-utility-nix/actions/runs/45826063836).
These runs predate the version bump; verify the final `v1.0.0` Tag's own CI and
cache uploads when publishing. Build success does not establish hardware support.

**Other Epson models and native Epson network maintenance remain unverified.**
Remote IPP printing through the NixOS host does not validate direct network
discovery, status, cleaning or cross-subnet operation. aarch64 printer hardware,
maintenance triggered during printing, full GUI maintenance interaction and timer
activation also remain unverified. No all-model compatibility claim is made.
See the [dated validation record](https://github.com/SunnyPai0413/epson-printer-utility-nix/blob/v1.0.0/validation/README.md)
for local release checks, evidence provenance and historical results.

## Source and licenses

The original source RPM/tarballs, checksums, upstream notices and third-party
licenses remain preserved. New code is GPL-2.0-or-later; upstream files retain
their individual licenses and exceptions. Adapted upstream files carry dated
modification notices and the packages include their generated file list.
See [NOTICE.md](https://github.com/SunnyPai0413/epson-printer-utility-nix/blob/v1.0.0/NOTICE.md)
and [source provenance](https://github.com/SunnyPai0413/epson-printer-utility-nix/blob/v1.0.0/upstream/SOURCE.md).
