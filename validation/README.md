# Validation record

Dates use Asia/Singapore. This directory is evidence, not an installation or
maintenance tutorial. Follow the top-level README for installation and usage.
Machine names, process IDs and store hashes in historical text logs have been
redacted; source SHA-256 values are retained unchanged.

## Project 0.2.0 — 2026-11-26

Current x86_64-linux builds and flake checks pass. They cover:

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

Unverified: network printers, other printer models, actual CUPS page output and
maintenance during printing, complete NixOS module activation, aarch64 builds and
new GUI maintenance interaction on hardware. Parser/FIFO fixtures do not establish
hardware compatibility. New USB/network raw color metadata and counters must not
be presented as universally supported.

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
