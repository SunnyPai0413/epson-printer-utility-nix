# Validation record

Dates use Asia/Singapore. This directory is evidence, not an installation or
maintenance tutorial. Follow the top-level README for installation and usage.
Machine names, process IDs and store hashes in historical text logs have been
redacted; source SHA-256 values are retained unchanged.

## v1.0.0 release validation — 2026-11-26

Project version is `1.0.0`; the release Tag is `v1.0.0`. Upstream remains Epson
Printer Utility `1.1.3` / epson-backend `1.3.1`. The project is NixOS-first;
hardware evidence covers a USB L805 on NixOS x86_64, not all Epson models.

### Printing and reboot confirmation

The maintainer supplied the following completed results on 2026-11-26 for this
release record:

- L805 remote IPP multi-page PDF printing completed successfully after the ecblp
  FIFO backpressure fix (`2cb2500`).
- After the persistent tmpfiles ACL fix (`138ad2f`), reboot verification passed
  for runtime ACLs, the CUPS service and print jobs.

The tested path was **remote client → IPP → NixOS CUPS → model driver → ecblp/ecbd
→ USB L805**. This verifies CUPS sharing and USB transport, not Epson's direct
network maintenance protocol. The backpressure fix keeps cancellation possible
and fails on reader loss without replaying print data. The ACL fix restores `lp`
group access to runtime FIFO/locks after reboot and covers files recreated by ecbd.

These hardware/reboot results are maintainer confirmations supplied for release
preparation; new raw hardware transcripts are not included. Existing raw JSON and
logs retain the versions and dates of the earlier runs. Version/documentation
preparation does not repeat cleaning or submit additional physical print jobs.

### Native CI builds and Cachix publishing

GitHub Actions reports successful builds, cache setup and post-job uploads for
baseline commit `138ad2f59c20750c66e73173aa0990a27a259335` on 2026-11-26:

| System | Native runner | Build and Cachix upload evidence |
| --- | --- | --- |
| `x86_64-linux` | `ubuntu-24.04` | [Successful run 45826063829](https://github.com/SunnyPai0413/epson-printer-utility-nix/actions/runs/45826063829) |
| `aarch64-linux` | `ubuntu-24.04-arm` | [Successful run 45826063836](https://github.com/SunnyPai0413/epson-printer-utility-nix/actions/runs/45826063836) |

Each run built the default suite, utility and backend, including package CTests,
then completed both `Publish successful outputs to Cachix` and its post step.
CI does not run printer hardware tests or the separate flake module/source checks.
These runs precede the version bump; the final `v1.0.0` Tag needs its own two CI
runs and cache uploads. No Tag or Release is created by preparing this record.

### Local release checks and remaining limits

The v1.0.0 working-tree build and flake check results are recorded separately in
[`v1.0.0-checks.txt`](v1.0.0-checks.txt). Original source archives, license texts,
print/maintenance code and NixOS service logic are unchanged by release preparation.

Unverified: all other Epson models; direct Epson network discovery, status and
maintenance; cross-subnet network operation; aarch64 printer hardware; full GUI
maintenance interaction; timer activation; deliberately invoking maintenance
during printing; native installation integration on other Linux distributions.
Fixtures and successful builds do not establish hardware compatibility.

### Retained L805 read-only evidence

[`current-usb.json`](current-usb.json) and [`current-gui.txt`](current-gui.txt)
are internal 0.2.0 evidence retained unchanged. They establish L805 USB enumeration,
status, ink IDs/unknown values, feed counters, ecblp discovery and desktop GUI
startup. Historical nozzle/cleaning records are accounted for below. Their earlier
unverified lists are superseded by the printing, reboot and CI evidence above.

## Retained internal 0.2.0 evidence — earlier on 2026-11-26

The internal x86_64-linux builds and flake checks passed at that stage. They covered:

- Original source RPM, both tarballs and extracted spec SHA-256.
- Epson's USB parser: status/error/warning independence, cancellation, no guessed
  colors, variable ink lists, original identifiers, unknown levels, true zero,
  malformed/absent counters and byte order.
- Epson's native network binary parser: independent warnings/faults, native color
  type/ID, unavailable ink, missing counters and multi-byte counter arithmetic.
- Shared GUI/CLI report model, all known USB-to-EPS error mappings, distinct black
  variants, non-six-color and duplicate entries, null handling and device selectors.
- Offline USB and network CLI, rejected unsupported commands/unauthorized cleaning,
  scheduled skip semantics and successful empty enumeration without ecbd.
- Actual ecblp executable against a temporary FIFO: discovery, byte-exact transfer,
  maintenance-lock exclusion, absent reader and disappearing reader failure.
- NixOS module evaluation: USB permissions, default timer off, no catch-up/restart,
  native-ID schedule selection, network-only without USB daemon/package/rules,
  optional CUPS driver and access group, no generated queues or open ecbd port.

A separate fresh local Git checkout with the final uncommitted changes applied
successfully built the default package and passed all four flake checks. No .work,
result links or prepared source trees were copied, and no commit was created.
The working tree and fresh checkout produce the same package source after Python
bytecode caches are excluded. See `current-checks.txt` for the concise final record.

L805 read-only hardware regression passed using the final 0.2.0 packages;
see `current-usb.json`. A temporary ecbd was started for these queries and stopped
in cleanup. CUPS was active both before and after; no maintenance or print command
was sent. This regression read:

- One native USB device (`USB`; this device's 1284 ID did not supply a serial).
- Idle status, error none, warning mask zero.
- Six inks in device order: cyan, magenta, light-magenta, light-cyan, black, yellow.
  Actual ST2 type/color IDs were retained. All raw values remain 105 / NOREAD,
  display disabled, percentages null. The old photo-black-by-count guess is gone.
- Native feed counters: color 83,594; monochrome 1,497; total 85,091. Blank 77,
  color borderless 2,177, monochrome borderless 0, ADF unavailable. These are device
  reports, not independently measured successful prints.
- Native ecblp discovery found the shared runtime FIFO, without submitting a job.

The final GUI was also smoke-tested in a real X11/XWayland session with ecbd
stopped (`current-gui.txt`); no maintenance interaction was executed.

At that earlier stage, CUPS page output, reboot persistence and aarch64 builds
had not yet been verified; the release record above supersedes those gaps. The
other hardware limitations still apply. Parser/FIFO fixtures do not establish
hardware compatibility. USB/network raw color metadata and counters must not be
presented as universally supported.

## Retained L805 predecessor evidence — 2026-11-25–26

The historical JSON files predate schema 2 and the current adapters. Do not use
those files as a current JSON contract or assume the old fixed six-row mapping.
In particular, the old USB converter inferred photo black from six cartridges;
0.2.0 retains the actual ID instead.

- `status*.json`: L805 USB reported idle / no error.
- `ink.json`: six returned colors; native raw level 105 / NOREAD, display disabled,
  percentages explicitly unknown. This was not an actual liquid measurement.
- `physical-confirmation.txt`: human confirmation of initial nozzle output and
  ordinary cleaning; yellow nozzle pattern initially unclear. An initial software
  result was unconfirmed after follow-up communication failure, with no auto replay.
- `clean.json`, `y-clean-round-{1,2,3}/`: initial one ordinary clean plus three later,
  individually authorized rounds of two ordinary cleans and one nozzle check each.
  **Seven total historical ordinary-clean invocations**, not only the one in the
  earlier summary. These are evidence of past authorization, not a recommendation
  to repeat that sequence. Last-round physical pattern quality was not confirmed.
- `nozzle-service*`: the scheduled command's oneshot service was run manually;
  timer stayed disabled. New timer activation has not been tested on hardware.
- `gui-*.txt` / `gui-*.log`: the prior native GUI launched in a real desktop session;
  its offline window was observed. This does not prove the new asynchronous guide.
- `build-final.log`, `flake-check.log`, `devshell.log`: prior builds/checks/shell;
  these old names do not refer to the final 0.2.0 build.

CUPS remained active during the recorded predecessor session. Temporary ecbd was
stopped afterward. `result-summary.txt` is an earlier partial summary, superseded
by the later round records and this combined accounting. `runtime-test.sh` is a
historical developer helper, not the supported installation path.
