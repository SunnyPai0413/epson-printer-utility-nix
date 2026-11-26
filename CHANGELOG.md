# Changelog

## 1.0.0 — 2026-11-26

First formal public release; Git Tag: `v1.0.0`. NixOS-first packaging and
integration, with Nix packages also usable on other Linux distributions; no
native installer or service integration is supplied for those distributions.

Upstream remains Epson Printer Utility 1.1.3 / epson-backend 1.3.1.

- Restore native network discovery and connections, independently of ecbd/USB.
- Share USB status/error/warning mappings, actual ink lists and native feed counters between GUI and CLI.
- Add `devices` and `paper-count`; preserve the four existing CLI commands.
- JSON schema 2: variable ink lists, distinct black variants, independent warnings and communication outcome; see docs/JSON.md.
- Build/install native ecblp; optional NixOS CUPS integration with shared FIFO paths and locks.
- Let ecblp wait through sustained FIFO backpressure, retaining cancellation and no replay on failure; log I/O stages, errno and poll events.
- Restore CUPS backend FIFO/lock access persistently with tmpfiles ACLs, including after reboot.
- Run GUI maintenance waits in a worker; retain one-command, fail-closed scheduled maintenance.
- Add public installation, source/license and validation documentation.
- Mark every adapted upstream source file with a dated modification notice and install its generated file list.
- Validate L805 remote IPP multi-page PDF printing through NixOS CUPS and the USB
  backend on 2026-11-26; reboot checks passed for ACLs, CUPS and print jobs.
- Document Windows Epson driver access through a separate CUPS IPP RAW queue,
  coexisting with the normal ESC/P-R queue and reusing ecblp/ecbd and shared locks;
  explain RAW deprecation and the CUPS 3 migration limit.
- Record maintainer-confirmed L805 Windows Epson driver high-quality A4 photo-paper
  printing, nozzle check and Power Ink Flushing on 2026-11-26. Flushing is supplied
  by the Windows driver, not this project's maintenance API. Actual ink-placement
  DPI, CD/DVD printing and Windows bidirectional status remain unverified.
- Complete native x86_64-linux/aarch64-linux CI builds and Cachix publishing for
  the pre-release baseline; the final versioned Tag still needs its own CI runs.
- Document fixed-Tag installation, L805 driver/queue setup and optional IPP
  sharing. Other Epson models and native network maintenance remain unverified;
  successful builds do not imply hardware compatibility.

This release consolidates the internal 0.2.0 draft. JSON schema 2 differs from
the local predecessor; project version 1.0.0 does not change the upstream versions
or the JSON schema number. See the [validation context](.agents/VALIDATION.md)
for release background, dated evidence and remaining limits.
Documentation supplements retain version 1.0.0 and existing Git Tags. User guides
are consolidated under docs/; architecture, adaptation, decisions, development
and validation context are indexed by AGENTS.md under .agents/. Program code,
NixOS modules, tests and build settings are unchanged.

## 0.1.0 (local predecessor)

USB L805 maintenance adaptation using the same upstream sources, GUI, four-command CLI and optional nozzle timer.
