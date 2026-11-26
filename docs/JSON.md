# CLI JSON schema 2

[返回首页](../README.md) · [安装配置](INSTALL.md) · [打印配置](PRINTING.md)

Project v1.0.0 preserves `status`, `ink`, `nozzle-check`, `clean`, `--json`,
`--confirm-clean`, and `nozzle-check --scheduled`; it adds `devices`, `paper-count`
and `--connection all|usb|network`. In this release, `project_version` is `1.0.0`,
`schema_version` remains `2`, `upstream_utility_version` is `1.1.3` and
`upstream_backend_version` is `1.3.1`. These version numbers are independent.

## Compatibility changes from local pre-release clients

- `schema_version` is now `2`. Project and both upstream versions are separate fields.
- `ink` is the **actual reported list, in reported order**, with zero to twenty entries.
  It is no longer a fixed six-row list. Missing color IDs produce `[]`, not six
  invented unknown slots. Duplicate entries remain separate and have an `index`.
- `black`, `photo-black`, `matte-black` and `black-2` are distinct. Labels are stable
  English color names, not the former six translated labels. Match a color by its
  ID/name, never by array index or a six-color assumption.
- `device_color_code` remains the shared EPS color enum. `reported_color_id` adds the
  reported identifier, or `null` when unavailable. `color_id_format` is
  `ink-identifier` (original textual INK ID), `st2-type-color` (two-byte cartridge
  type/color, type in the high byte), or `unavailable`. Unknown color names remain
  `unknown` with their reported ID retained. Internal USB ST2 conversion preserves
  the original ID alongside the native textual INK representation. Legacy color
  names inferred from cartridge count may therefore change.
- Known errors now have specific names/codes, including maintenance-box-full,
  maintenance-required, double-feed, ink-cover-open and the other native conditions.
  The existing names `none`, `paper-out`, `paper-jam`, `ink-out`, `cover-open` remain.
  Numeric `status_code`/`error_code` use the **shared EPS enum**, not the ECB enum or
  the on-wire ER/ST byte. Applications should prefer the named fields.
- `warnings` is an independent list of `paper-low`, `maintenance-box-near-end`,
  `maintenance-required`, `check-nozzle`, `cut-trash-full`. `warning_mask` is the
  corresponding five-bit mask. Warnings do not replace a device error or force a
  busy printer to idle. Ink low/unreadable conditions also remain in each ink entry.
- `communication` is `ok`, `failed` or `unknown`. A successfully received device
  fault has `communication: "ok"`, its device status and detailed `error`.
  A connection/status query failure has `communication: "failed"`,
  `status: "unknown"`, `error: "communication-error"`, with a distinct `reason`.
  A discovery miss leaves communication/status/error unknown; it does not assert a
  printer fault. A successful report can itself contain a native communication
  error code; `ok` only says the status response was received.
- A reported `paper_count` object accompanies successful status queries. Each missing,
  malformed or unsupported native count is `null`. The native signed 32-bit API's
  out-of-range values are unavailable rather than overflowing; the computed total
  uses 64-bit arithmetic.

## Fields

All responses include `command`, `device`, `status`, `error`, `communication`,
`warnings`, `outcome`, `reason`, `schema_version`, `project_version`,
`upstream_utility_version`, `upstream_backend_version`.

After selection, `device` keeps the model name for compatibility. `device_info`
contains `id`, `model`, `connection`, `protocol`, `location`, `serial`. `devices`
returns an array with that same shape; a successful empty discovery returns
`outcome: "reported", devices: []`. Only discovered devices may be selected by
address; an arbitrary undiscovered address is not manufactured into a printer.
USB IDs use the device's 1284 serial when available; they otherwise remain `USB`,
referring to the daemon's one selected printer. `device.serial` in the NixOS module
filters the USB descriptor; those two serial representations can differ.

An `ink` entry contains:

```json
{
  "index": 0,
  "color": "photo-black",
  "label": "photo-black",
  "device_color_code": 13,
  "reported_color_id": 41280,
  "color_id_format": "ink-identifier",
  "reported_percent": null,
  "reported_raw": 105,
  "native_ink_status": -4,
  "source": "ink-info-disabled-by-device"
}
```

This is an illustrative original textual INK report, not a claim about current
L805 output. `reported_percent` is numeric only when the device allows display,
the native ink status is nonnegative, and the reported value is in 0–100. True zero
stays zero; no rounding is added. Other sources are `device-reported` and
`device-value-unavailable`. `reported_raw` retains the native API value/sentinel,
not necessarily the network packet byte. No ink value measures physical liquid.

`paper_count` contains `color`, `monochrome`, `blank`, `adf`, `color_borderless`,
`monochrome_borderless`, `total`, and `meaning`. Total is color + monochrome only
when **both** exist; otherwise it is null. No fallback treats missing counts as
zero or adds blank/ADF counts. Counts describe native paper feed categories, not
successful print pages, and there is no reset command. `paper-count` returns
unavailable when no counter is available; partially available reports retain nulls.

Maintenance adds `native_result` if the guarded native operation was attempted.
`submitted` means one native command was sent and the follow-up status became idle;
physical output/cleaning still requires human confirmation. `unconfirmed` means
native submission or follow-up could not be confirmed, with no retry. Do not
interpret either as a measured print-quality result.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Report returned, one maintenance operation submitted, or scheduled task skipped/unconfirmed (see outcome) |
| 2 | Invalid command/arguments; `clean` without `--confirm-clean` |
| 3 | Unavailable report or manual maintenance skipped (offline, ambiguous, busy, locked, device fault) |
| 4 | Manual maintenance unconfirmed; never automatically replay it |

A successfully reported device error still exits 0: inspect `status` and `error`.
`--scheduled` is accepted only for `nozzle-check`; it never cleans, retries,
queues a missed run or returns a false `submitted` outcome for a skip.
