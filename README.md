# sen-TapIn — NFC Access & Attendance Terminal

**v0.1.0 (baseline), build variant `+mp` (MicroPython, Layer 1)**

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
card. The attendance log `attendance.csv` is created automatically on
first event (schema: `timestamp,uid,name,direction,result`).

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
