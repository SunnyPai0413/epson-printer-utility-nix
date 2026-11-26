# Changelog

## 0.2.0 (unreleased)

Upstream remains Epson Printer Utility 1.1.3 / epson-backend 1.3.1.

- Restore native network discovery and connections, independently of ecbd/USB.
- Share USB status/error/warning mappings, actual ink lists and native feed counters between GUI and CLI.
- Add `devices` and `paper-count`; preserve the four existing CLI commands.
- JSON schema 2: variable ink lists, distinct black variants, independent warnings and communication outcome; see docs/JSON.md.
- Build/install native ecblp; optional NixOS CUPS integration with shared FIFO paths and locks.
- Let ecblp wait through sustained FIFO backpressure, retaining cancellation and no replay on failure; log I/O stages, errno and poll events.
- Run GUI maintenance waits in a worker; retain one-command, fail-closed scheduled maintenance.
- Add public installation, source/license and validation documentation.
- Mark every adapted upstream source file with a dated modification notice and install its generated file list.

## 0.1.0 (local predecessor)

USB L805 maintenance adaptation using the same upstream sources, GUI, four-command CLI and optional nozzle timer.
