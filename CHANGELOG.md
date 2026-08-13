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


