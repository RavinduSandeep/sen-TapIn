# Changelog

All notable changes to sen-TapIn are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is `MAJOR.MINOR.PATCH` with
the build-variant suffix `+mp` (MicroPython, Layer 1).

**The firmware version is declared once only in `version.py`.** Every released entry below must
correspond to a `version.py` value that was actually flashed to hardware. If those two ever
disagree, the changelog is wrong.

## How to add an entry

Add to `[Unreleased]` as you work — not at release time, when you have forgotten what you did.
Group under `Added`, `Changed`, `Fixed`, `Removed`, or `Safety`. Reference the requirement or
document section where one applies (`REQ-F-004`, `CS-003 §7`, `HDD-003 §3.3`). Write for someone
diagnosing a fault on a deployed terminal after few months from now.

Anything that changes behaviour a user of the terminal can observe — a screen, a tone, a colour,
a timing — should be written here even if the code change was one line.

---

## [Unreleased]

Nothing yet.

## [0.2.0+mp] — hardware-verified 2026-08-17

Network check-in. The terminal associates to Wi-Fi, fetches a manifest, compares its roster
revision against it, and reports what it is running. **It does not download or replace the
roster** — that is the next issue.

### Added
- `net.py` — Wi-Fi association and a minimal HTTP(S) GET. Association is incremental via
  `net_tick()`, which returns immediately and never waits on the radio. No function in this
  module raises; every one returns a status.
- `sync.py` — check-in policy: reads `terminal.conf`, decides when a check-in is due, fetches
  and parses the manifest, composes the idle-screen status line.
- `sd-card/terminal.conf` — template for SSID, password, terminal id and manifest URL. Lives on
  the card, never in the repository, so credentials are not committed and one identical firmware
  image runs on every terminal.
- Version reporting: terminal id, firmware and local revision go up as query parameters on the
  manifest fetch, so the server's ordinary access log answers "what is each terminal running?"
  without a second endpoint to build or maintain.
- Sync age on the idle screen, flagged with `!` past `SYNC_STALE_MS`.
- `SYNC` / `SYNC_FAIL` records in `events.log`.
- Network tuning constants in `config.py`.

### Changed
- `ui.ui_show_idle()` takes an optional `sync_text`. Empty when networking is not configured, so
  a terminal without Wi-Fi looks exactly as it did before.
- `main._run()` drives `net_tick()` on each pass through IDLE and tracks `idle_since`.
- `main.main()` drops the association on fault.

### Safety
- **Networking is not in the fault chain.** `_network_init()` runs after `_startup()` has passed
  all its checks, and returns nothing. A missing `terminal.conf`, a wrong password or a dead
  router leaves the terminal granting, denying and logging exactly as before, on the roster
  already on its card. This is the single most important property of the change (REQ-NF-007).
- **The blocking fetch is gated.** `net_http_get()` blocks up to `HTTP_TIMEOUT_MS` (2 s). It runs
  only from IDLE, only after the terminal has been tap-free for `SYNC_IDLE_GUARD_MS` (3 s). The
  guard makes a mid-tap fetch unlikely; it does not make it impossible. This is the review point
  — see the change description.
- Staleness is shown rather than hidden: an offline terminal is still enforcing an old roster,
  including revoked badges, and has no way to know it is wrong.
- Response body capped at `HTTP_MAX_BODY` so a misconfigured URL cannot exhaust RAM.

### Security
- The security of roster sync rests entirely on the private signing key, which never leaves the
  build machine. Compromise of any terminal — including physical possession of its SD card — must
  not enable roster forgery. This is why the scheme is asymmetric (Ed25519): the terminal holds
  only a public key, which needs integrity but not secrecy.
- No signature verification happens in this build, because nothing is downloaded. The manifest is
  read for a revision number; nothing in it is trusted or acted on.

### Fixed (review pass before landing on main)
- `config.TERMINAL_CONF_PATH` was referenced by `main._network_init()` but never defined, so every
  boot died with an `AttributeError` before the fault chain could catch it — with or without Wi-Fi.
  Added the constant to `config.py`.
- `sd-card/terminal.conf` was committed despite its own header saying it must never be (it is where
  the Wi-Fi password goes, and `.gitignore` cannot untrack an already-tracked file). Renamed to
  `terminal.conf.example` so only the placeholder template is in the repository; the ignore rule
  now actually protects the filled-in file.
- `version.py` still said `0.1.2` while this entry declares `0.2.0`, so the boot screen and the
  check-in's `fw=` parameter would have reported the wrong version — the exact disagreement
  `version.py` exists to prevent. Bumped to `0.2.0`.
- Restored the "A note on review" section of `CONTRIBUTING.md`, deleted without mention.
- Removed a duplicated REQ-F-011 stretch-goal paragraph in `README.md` and pointed its setup
  instructions at the renamed template.

### Hardware verification (2026-08-17, Pico 2 W / RP2350, MicroPython 1.25.0-preview)
- I2C scan found every HDD-003 §3.1 device at its frozen address: PN532 0x24, SSD1306 0x3C,
  DS3231 0x68 (plus the DS3231 module's on-board AT24C32 EEPROM at 0x57, unallocated).
- PN532 answered GetFirmwareVersion (IC 0x32, firmware 1.6) and accepted SAMConfiguration.
- Card reads: UID 17C410C2 returned identically on three consecutive polls via the
  non-blocking start_listen / read_uid path main._run() uses.
- Standalone boot on the deployed build logged `BOOT,fw=0.2.0+mp rev=1`; with no terminal.conf
  present, _network_init() disabled networking without faulting, as designed.
- End-to-end taps: known card granted with auto-toggled direction (OUT then IN) and recorded
  to attendance.csv; unknown card E73624C2 correctly DENIED with no direction.
- Wi-Fi check-in against a LAN manifest server: association and first check-in 7 s after boot;
  server access log received `GET /manifest.json?id=dev-bench&fw=0.2.0&rev=1`; terminal logged
  `SYNC,rev 2 available (local 1)` — the correct comparison of manifest rev 2 to local rev 1.

## [0.1.2+mp] — merged (PR #3)

Version identity: the terminal can now state what firmware it runs and what roster it enforces.
Groundwork for remote roster sync; contains no networking of any kind.

### Added
- `version.py` — the single declaration of the firmware version, applying the CS-003 §3 principle
  already used for the pin map in `board.py`. Referenced nowhere else by literal value.
- `sd_log.sd_allowlist_rev()` — reads an optional `# rev: N` marker from `allowlist.txt`. Missing
  or malformed reads as revision `0` and is not a fault.
- `sd_log.log_event()` and a new `/sd/events.log`, carrying one `BOOT` record per power-up
  (`timestamp,BOOT,fw=0.1.2+mp rev=N`). Diagnostic only; not part of the REQ-SPEC-003 §4 record.
- `config.EVENTS_PATH`.
- `# rev:` marker in `sd-card/allowlist.txt` and in the template `sd_log.py` writes when no
  allow-list is present.

### Changed
- `ui.ui_show_boot()` now takes `(version_text, rev=None)` instead of hardcoding its text. The
  string is composed in `main.py` so the display layer continues to decide nothing (CS-003 §2).
- `main._startup()` draws the boot screen before the card mounts (preserving the early
  "OLED works" signal during bring-up), then redraws with the revision via the new
  `main._record_boot()` once `sd_ensure_allowlist()` succeeds.
- `access.py` REQ-S-002 security notice reworded to drop the version numbers it named. The
  substance of the warning is unchanged.
- Module header comments no longer carry a version.
- `README.md` — version, `version.py` in the CS-003 §2 module table, and documentation of both the
  revision marker and `events.log`.

### Fixed
- **Boot screen reported the wrong version.** `ui_show_boot()` displayed a hardcoded
  `"v0.1.0 (+mp)"` while `ui.py`'s own header comment claimed `v0.1.1`. This was the only version
  string that left the device, so a fault reported from a deployed terminal could not be trusted to
  identify what was running.
- Version strings had drifted across the tree: `board.py` and `ui.py` at `v0.1.1`, all other
  modules and the README at `v0.1.0`, with no record of which was current.
- `sd_log.py` line 1 read `# 2sd_log.py` — stray leading character.

### Safety
- `log_event()` deliberately does **not** fail closed, unlike `log_append()`. A failed write is
  printed to serial and ignored. `log_append()` fails closed because attendance is the audit record
  (CS-003 §5, REQ-NF-003); `events.log` is diagnostic, and inheriting fail-closed behaviour would
  let a full or unwritable card take a working terminal out of service over a record nothing
  depends on. The asymmetry is documented in the function docstring so it is not "corrected" later.
- `attendance.csv` is untouched — no new column, no schema change, byte-identical record format.
  The schema is specified in REQ-SPEC-003 §4 and `_directions_from_lines()` indexes it positionally,
  making it load-bearing for the auto-toggle state as well as for audit.
- Two references to `v0.1.0` remain, in `board.py` and `main.py`, describing the release whose
  safety scope REQ-S-001 defines ("indicator LED only — never a lock or mains load"). These are
  specification references rather than module self-identification and were left deliberately.

### Verification
- All modules parse; `sd_allowlist_rev()` exercised against seven marker variants plus a missing
  file, with allow-list parsing confirmed unchanged in each; boot screen lines confirmed to fit the
  16-character font width and 64 px panel in both draw states.
- Bench-verified and merged in PR #3.


## [0.1.2+mp] — pending hardware verification

Version identity: the terminal can now state what firmware it runs and what roster it enforces.
Groundwork for remote roster sync; contains no networking of any kind.

### Added
- `version.py` — the single declaration of the firmware version, applying the CS-003 §3 principle
  already used for the pin map in `board.py`. Referenced nowhere else by literal value.
- `sd_log.sd_allowlist_rev()` — reads an optional `# rev: N` marker from `allowlist.txt`. Missing
  or malformed reads as revision `0` and is not a fault.
- `sd_log.log_event()` and a new `/sd/events.log`, carrying one `BOOT` record per power-up
  (`timestamp,BOOT,fw=0.1.2+mp rev=N`). Diagnostic only; not part of the REQ-SPEC-003 §4 record.
- `config.EVENTS_PATH`.
- `# rev:` marker in `sd-card/allowlist.txt` and in the template `sd_log.py` writes when no
  allow-list is present.

### Changed
- `ui.ui_show_boot()` now takes `(version_text, rev=None)` instead of hardcoding its text. The
  string is composed in `main.py` so the display layer continues to decide nothing (CS-003 §2).
- `main._startup()` draws the boot screen before the card mounts (preserving the early
  "OLED works" signal during bring-up), then redraws with the revision via the new
  `main._record_boot()` once `sd_ensure_allowlist()` succeeds.
- `access.py` REQ-S-002 security notice reworded to drop the version numbers it named. The
  substance of the warning is unchanged.
- Module header comments no longer carry a version.
- `README.md` — version, `version.py` in the CS-003 §2 module table, and documentation of both the
  revision marker and `events.log`.

### Fixed
- **Boot screen reported the wrong version.** `ui_show_boot()` displayed a hardcoded
  `"v0.1.0 (+mp)"` while `ui.py`'s own header comment claimed `v0.1.1`. This was the only version
  string that left the device, so a fault reported from a deployed terminal could not be trusted to
  identify what was running.
- Version strings had drifted across the tree: `board.py` and `ui.py` at `v0.1.1`, all other
  modules and the README at `v0.1.0`, with no record of which was current.

### Safety
- `log_event()` deliberately does **not** fail closed, unlike `log_append()`. A failed write is
  printed to serial and ignored. `log_append()` fails closed because attendance is the audit record
  (CS-003 §5, REQ-NF-003); `events.log` is diagnostic, and inheriting fail-closed behaviour would
  let a full or unwritable card take a working terminal out of service over a record nothing
  depends on. The asymmetry is documented in the function docstring so it is not "corrected" later.
- `attendance.csv` is unchanged.

### Verification
- All modules parse; `sd_allowlist_rev()` exercised against seven marker variants plus a missing
  file, with allow-list parsing confirmed unchanged in each.
- **Not yet run on hardware.** Bench check required before merge — in particular whether the two
  boot-screen draws read as an update or as a flicker.

## [0.1.1+mp] — not recorded

`board.py` and `ui.py` carried this version; no other module or document did, and no record exists
of what changed or when it was flashed.

## [0.1.0+mp] — baseline

First working terminal, per REQ-SPEC-003, HDD-003 and CS-003, with the following deviations from
those documents recorded at bring-up. All remain outstanding as document revisions owned by the
Lead Engineer.

(here write about the v0.1.0+mp)


