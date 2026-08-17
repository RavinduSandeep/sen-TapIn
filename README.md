# sen-TapIn — NFC Access & Attendance Terminal

**v0.1.2, build variant `+mp` (MicroPython, Layer 1)** — the version is
declared once in `version.py` and shown on the boot screen.

Firmware for the Raspberry Pi Pico 2 W terminal defined by:

- **REQ-SPEC-003** — Requirements Specification
- **HDD-003** — Hardware Design Document (frozen pin map, §3)
- **CS-003** — Coding Standard (module layout, naming, state machine)

## Build deviation — no IN/OUT buttons, auto-toggle direction

This hardware build does **not** fit the two IN/OUT mode buttons of
HDD-003 §3.3 / REQ-F-002. Instead (per the sen-TapIn.png process flow):

- The terminal is **always listening** — tap a card any time from the
  idle clock screen (no arming step, so REQ-F-003's arm timeout does
  not apply).
- **Direction auto-toggles per card**: a card's first granted tap logs
  `IN`, its next logs `OUT`, and so on. The toggle state is rebuilt
  from `attendance.csv` at start-up, so it survives power cycles.
- **10 s same-card delay**: after a decided tap, the same card is
  ignored for 10 s (`DUP_SUPPRESS_MS`) — it cannot double-toggle or
  spam the log while resting on the reader. Different cards are
  unaffected.
- Denied taps are logged with direction `-` (no toggle state).
- GP13/GP14 are unallocated; the state machine drops the
  ARMED_IN/ARMED_OUT states.

These are deviations from REQ-SPEC-003 §2 (REQ-F-002/003/012) and
HDD-003 Rev 1.0 — record them as document revisions (the Lead Engineer
owns both documents).

## Module layout (CS-003 §2)

| File | Responsibility |
|---|---|
| `version.py` | Single source of the firmware version string. |
| `board.py` | Single source of pin numbers and I2C addresses (HDD-003 §3). No logic. |
| `config.py` | Tunable constants (delays, colours, tones, file paths) — CS-003 §9. |
| `rtc.py` | DS3231 read/set; timestamps for logging. |
| `nfc.py` | PN532 UID read over I2C (minimal driver, non-blocking poll). |
| `sd_log.py` | SD mount, allow-list read, append-only log, toggle-state rebuild. |
| `ui.py` | OLED, WS2811 RGB, and buzzer feedback. |
| `access.py` | Allow-list lookup and the grant/deny decision. |
| `main.py` | State machine (IDLE / DECIDING / FEEDBACK / LOGGING / FAULT). |
| `lib/ssd1306.py` | Third-party OLED driver (micropython-lib). |
| `lib/sdcard.py` | Third-party SD SPI driver (micropython-lib). |

`sd-card/allowlist.txt` is a template to copy to the root of the MicroSD
card. It carries an optional `# rev: N` marker: bump it whenever the
roster is edited and the terminal will show that number at boot, so a
deployed unit can be asked which roster it is enforcing. A missing or
unreadable marker reads as revision 0 and is not a fault.

The attendance log `attendance.csv` is created automatically on first
event (schema: `timestamp,uid,name,direction,result`).

A second file, `events.log`, records one line per power-up
(`timestamp,BOOT,fw=... rev=...`). It is diagnostic only and is **not**
part of the REQ-SPEC-003 §4 record: unlike `attendance.csv`, a failed
write to it is reported on serial and ignored, so a full or unwritable
card can never stop the terminal from deciding and logging attendance.

## Install

1. Flash MicroPython (RPI_PICO2_W build) to the Pico 2 W.
2. Copy all `.py` files and the `lib/` folder to the board
   (Thonny, or `mpremote cp -r . :`).
3. Prepare the SD card (FAT32) with `allowlist.txt` at its root.
4. Set the RTC once from the REPL — see the wiring & setup PDF.
5. Reset: `main.py` runs automatically.

Full wiring instructions, bring-up checklist, and troubleshooting are in
[`docs/WIRING.md`](docs/WIRING.md) (Markdown) and
[`docs/sen-TapIn_Wiring_and_Setup.pdf`](docs/sen-TapIn_Wiring_and_Setup.pdf)
(original PDF); the process flow is
[`docs/sen-TapIn.png`](docs/sen-TapIn.png).

## Safety notes (REQ-SPEC-003 §5)

- The relay drives a **low-voltage indicator LED only** in v0.1.0 —
  never mains, never a solenoid/strike (REQ-S-001 / HDD REQ-HW-003).
- UID-based authorisation is **not secure** and is a learning baseline
  only (REQ-S-002 / HDD REQ-HW-002).
- On any fault the terminal fails closed: relay de-energised, no
  operation until the fault clears (REQ-S-003, REQ-NF-007).

The optional Wi-Fi log-viewing page (REQ-F-011) is a stretch goal and is
not implemented in this baseline.


## Networking (v0.2.0)

The terminal can check in to a manifest URL over Wi-Fi, compare its
roster revision, and report its firmware version. Copy
`sd-card/terminal.conf.example` to the card root as `terminal.conf` and
fill in the SSID, password, terminal id and manifest URL. The filled-in
file holds a password and is deliberately not in the repository — only
the placeholder template is.

**Networking is optional and cannot fault the terminal.** With no
`terminal.conf`, a wrong password or a dead router, the terminal grants,
denies and logs exactly as it did in v0.1.2, using the roster already on
its card. The idle screen shows the age of the last successful check-in,
flagged with `!` once it exceeds 24 h, because an offline terminal is
still enforcing an old roster — including any badges since revoked.

This build does **not** download or replace the roster. Downloading,
Ed25519 signature verification and the atomic swap follow separately.