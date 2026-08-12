# sen-TapIn — Wiring & Setup

NFC Access & Attendance Terminal — Raspberry Pi Pico 2 W + DS3231 + DFRobot NFC Module V2.0
(PN532) + 0.96″ IIC OLED (SSD1306) + MicroSD + WS2811 — button-less auto-toggle build.

This is the Markdown version of [sen-TapIn_Wiring_and_Setup.pdf](sen-TapIn_Wiring_and_Setup.pdf)
(v0.1.0, 31 July 2026). Pin map source: HDD-003 Rev 1.0 §3, with one deviation — the IN/OUT
buttons (GP13/GP14) are not fitted. Process flow: [sen-TapIn.png](sen-TapIn.png).

## 1. What you need

| Item | Role | Interface |
|---|---|---|
| Raspberry Pi Pico 2 W (RP2350) | Central controller | — |
| DFRobot Gravity UART & I2C NFC Module V2.0 (DFR0231-H, PN532) | NFC card reader, 13.56 MHz | I2C @ `0x24` |
| DS3231 RTC module (+ CR2032 coin cell) | Battery-backed timekeeping | I2C @ `0x68` |
| 0.96″ IIC OLED 128×64 (SSD1306) | User display | I2C @ `0x3C` |
| MicroSD card module (SPI, with on-board regulator/level shifter) + card | Allow-list + attendance log | SPI0 |
| WS2811 addressable RGB LED breakout | Status colour | Single-wire (GP12) |
| Passive buzzer | Grant / deny tones | PWM (GP15) |
| 2-channel relay board (only IN1 used) + low-voltage indicator LED | "Lock" indicator | GPIO (GP10) |
| Breadboard, jumper wires, micro-USB cable | Assembly / power | — |
| *Recommended:* 74AHCT125 level shifter | WS2811 data-line level (REQ-HW-004) | — |

Tools: a computer with Thonny (or `mpremote`), and one or more ISO 14443A test cards
(MIFARE Classic / NTAG).

## 2. Read this first — safety & constraints

> **Relay = indicator LED only (REQ-S-001 / HDD REQ-HW-003).**
> Do **not** connect mains voltage, a solenoid, a door strike, a motor, or any inductive load to
> the relay in v0.1.0. The relay channel switches a low-voltage indicator LED only. A real lock
> needs its own supply, a flyback diode, and a revision of HDD-003.

> **UID authorisation is not security (REQ-S-002 / HDD REQ-HW-002).**
> Card UIDs are trivially cloneable. sen-TapIn v0.1.0 is a learning and attendance baseline,
> not a security device.

- **Build deviation — no IN/OUT buttons; direction auto-toggles.** The terminal is always
  listening: tap a card any time. Each authorised card alternates direction automatically
  (first granted tap = IN, next = OUT, …), rebuilt from the SD log at start-up. The same card
  is then ignored for 10 s after a decided tap. GP13/GP14 are unallocated.
- **The rest of the pin map stays frozen (HDD REQ-HW-001).** Wire exactly as in §3; any change
  requires a revision of HDD-003 (and then one edit in `board.py` only).
- **Stay inside the USB current budget (HDD REQ-HW-005).** The SD module, relay board and
  WS2811 all share the 5 V VBUS rail from USB. Never power a real lock from VBUS.
- **Common ground is mandatory (HDD-003 §3.4).** Every module must share GND with the Pico.

## 3. Master pin map (frozen — HDD-003 §3)

| Pico 2 W GPIO | Physical pin | Function | Connects to |
|---|---|---|---|
| GP4 | 6 | I2C0 SDA | DS3231 SDA + SSD1306 SDA + PN532 SDA (shared) |
| GP5 | 7 | I2C0 SCL | DS3231 SCL + SSD1306 SCL + PN532 SCL (shared) |
| GP10 | 14 | Digital out | Relay board IN1 ("lock" indicator) |
| GP11 | 15 | Digital out | Relay board IN2 (spare — reserved, parked off) |
| GP12 | 16 | Timed serial | WS2811 DIN (via level shifter — see §4.5) |
| GP13 / GP14 | 17 / 19 | — | *Unallocated in this build. Leave unconnected.* |
| GP15 | 20 | PWM out | Passive buzzer (+) |
| GP16 | 21 | SPI0 MISO | MicroSD DO / MISO |
| GP17 | 22 | SPI0 CS | MicroSD CS |
| GP18 | 24 | SPI0 SCK | MicroSD CLK / SCK |
| GP19 | 25 | SPI0 MOSI | MicroSD DI / MOSI |
| 3V3 OUT | 36 | 3.3 V rail | DS3231 VCC, SSD1306 VCC, PN532 VCC |
| VBUS | 40 | 5 V rail (USB) | SD module VCC, relay board VCC, WS2811 5V, level-shifter VCC |
| GND | 3, 8, 13, 18, 23, 28, 33, 38 | Ground | All modules (single common ground) |

### Pico 2 W — used pins at a glance (top view, USB at top)

```
                          +-----[ USB ]-----+
                   GP0  1 |                 | 40 VBUS --> 5V rail (SD, relay, WS2811)
                   GP1  2 |                 | 39 VSYS
    GND rail <--   GND  3 |                 | 38 GND  --> GND rail
                   GP2  4 |                 | 37 3V3_EN
                   GP3  5 |                 | 36 3V3  --> 3.3V rail (RTC, OLED, NFC)
I2C0 SDA (bus) <-- GP4  6 |                 | 35 ADC_VREF
I2C0 SCL (bus) <-- GP5  7 |  Raspberry Pi   | 34 GP28
                   GND  8 |   Pico 2 W      | 33 GND
                   GP6  9 |  (top view,     | 32 GP27
                   GP7 10 |   USB at top)   | 31 GP26
                   GP8 11 |                 | 30 RUN
                   GP9 12 |                 | 29 GP22
                   GND 13 |                 | 28 GND
   Relay IN1 <-- GP10 14  |                 | 27 GP21
   Relay IN2 <-- GP11 15  |                 | 26 GP20
 WS2811 DIN <--  GP12 16  |                 | 25 GP19 --> SD MOSI (DI)
   (unused)      GP13 17  |                 | 24 GP18 --> SD SCK (CLK)
                   GND 18 |                 | 23 GND
   (unused)      GP14 19  |                 | 22 GP17 --> SD CS
  Buzzer (+) <-- GP15 20  |                 | 21 GP16 --> SD MISO (DO)
                          +-----------------+
```

## 4. Wiring, module by module

Power everything down (USB unplugged) while wiring.

### 4.0 Step 0 — rails

- Run a **GND rail** on the breadboard from any Pico GND pin (e.g. physical pin 3 or 38).
- Run a **3.3 V rail** from Pico **3V3 OUT (pin 36)** — feeds the I2C trio only.
- Run a **5 V rail** from Pico **VBUS (pin 40)** — feeds SD module, relay board, WS2811.

### 4.1 Shared I2C bus — DS3231 + SSD1306 + PN532

All three devices sit on the same two wires. Chain SDA→SDA→SDA, SCL→SCL→SCL.

| Module pin | DS3231 (`0x68`) | OLED (`0x3C`) | NFC Module V2.0 (`0x24`) | Pico connection |
|---|---|---|---|---|
| VCC | VCC | VCC | VCC (+) | 3.3 V rail (3V3, pin 36) |
| GND | GND | GND | GND (–) | GND rail |
| SDA | SDA | SDA | SDA (marked D/T on some revisions) | GP4 (pin 6) |
| SCL | SCL | SCL | SCL (marked C/R on some revisions) | GP5 (pin 7) |

> **NFC Module V2.0 mode selector: set it to I2C before first power-up.** The DFR0231-H speaks
> UART or I2C, chosen by its on-board switch. In UART mode the firmware reports "NFC not found".

**Pull-ups (HDD-003 §3.1):** the breakout boards carry their own SDA/SCL pull-ups — do not add
external ones. Fit the CR2032 coin cell in the DS3231 so time survives power cycles.

### 4.2 MicroSD module — dedicated SPI0 bus

| SD module pin | Pico connection |
|---|---|
| VCC | 5 V rail (VBUS, pin 40) — module has its own 3.3 V regulator + level shifting |
| GND | GND rail |
| CLK / SCK | GP18 (pin 24) |
| DI / MOSI | GP19 (pin 25) |
| DO / MISO | GP16 (pin 21) |
| CS | GP17 (pin 22) |

> If your SD breakout has **no regulator** (bare socket board), power it from 3.3 V instead —
> check your specific board before applying 5 V.

### 4.3 Relay board ("lock" indicator)

| Relay board pin | Pico connection |
|---|---|
| VCC | 5 V rail (VBUS, pin 40) |
| GND | GND rail |
| IN1 | GP10 (pin 14) |
| IN2 | GP11 (pin 15) — spare, held inactive by firmware |

**Indicator load on channel 1:** 3.3 V rail → COM; NO (normally open) → 330 Ω resistor → LED →
GND. Using NO means the LED is off unless the firmware pulses the relay — fail-closed (REQ-S-003).

> **Active-low boards:** many opto-isolated relay boards energise when IN1 is pulled LOW. If the
> relay clicks ON at boot, set `RELAY_ACTIVE_HIGH = False` in `config.py` — do not rewire.

### 4.4 Buzzer

| Buzzer pin | Pico connection |
|---|---|
| + (signal) | GP15 (pin 20) |
| – | GND rail |

The design calls for a **passive** buzzer (PWM tones). Note: the fitted module in this build is
an **active low-trigger** buzzer — see `BUZZER_LOW_TRIGGER` in `config.py`.

### 4.5 WS2811 RGB LED

| WS2811 pin | Pico connection |
|---|---|
| 5V / VCC | 5 V rail (VBUS, pin 40) |
| GND | GND rail |
| DIN (data in) | GP12 (pin 16) — via level shifter (recommended) |

> **Data-line level must be verified during bring-up (HDD REQ-HW-004).** The WS2811 is a 5 V
> part; the Pico drives 3.3 V logic. Robust option: a 74AHCT125 buffer — GP12 → 1A, 1Y → DIN,
> VCC = 5 V, GND common, 1OE̅ → GND.

If red and green appear swapped, set `WS2811_ORDER = "GRB"` in `config.py`. For 400 kHz parts,
set `WS2811_TIMING = 0`.

## 5. SD card preparation

1. Format a MicroSD card as **FAT32**.
2. Copy [`sd-card/allowlist.txt`](../sd-card/allowlist.txt) to the **root** of the card.
3. Add one line per authorised card: `UID,Name` — UID in uppercase hex, no separators; names
   must not contain commas; `#` lines are ignored (REQ-F-008).
4. Insert the card. `attendance.csv` is created automatically on the first event with header
   `timestamp,uid,name,direction,result`.

Tip: to learn a card's UID, tap it — the Denied event is logged with its raw UID. The allow-list
is re-read at every decision, so changes apply without a restart.

## 6. Firmware installation

1. **Flash MicroPython:** download the latest **Pico 2 W** (`RPI_PICO2_W`) UF2 from
   [micropython.org/download](https://micropython.org/download). Hold **BOOTSEL** while plugging
   in USB, drag the UF2 onto the `RP2350` drive.
2. **Copy the firmware** — all `.py` files plus `lib/`:

   ```sh
   pip install mpremote   # once
   mpremote cp board.py config.py rtc.py nfc.py sd_log.py ui.py \
               access.py main.py :
   mpremote mkdir lib
   mpremote cp lib/ssd1306.py lib/sdcard.py :lib/
   ```

3. **Reset** the board. `main.py` runs automatically at power-up.

## 7. Set the real-time clock (once)

Open a REPL, interrupt with `Ctrl-C`, then:

```python
from machine import I2C, Pin
import board, rtc
i2c = I2C(board.I2C_BUS_ID, sda=Pin(board.PIN_I2C_SDA),
          scl=Pin(board.PIN_I2C_SCL), freq=board.I2C_FREQ_HZ)
rtc.rtc_init(i2c)
rtc.rtc_set(2026, 7, 30, 9, 41, 0)   # year, month, day, hour, minute, second
rtc.rtc_now()                        # verify
```

The coin cell keeps this time across power cycles. `Ctrl-D` restarts the terminal.

## 8. First bring-up checklist

**I2C scan — must find exactly three devices:**

```python
from machine import I2C, Pin
import board
i2c = I2C(board.I2C_BUS_ID, sda=Pin(board.PIN_I2C_SDA),
          scl=Pin(board.PIN_I2C_SCL), freq=board.I2C_FREQ_HZ)
[hex(a) for a in i2c.scan()]   # expect ['0x24', '0x3c', '0x68']
```

| Address | Device | If missing, check |
|---|---|---|
| `0x24` | PN532 (DFR0231-H) | Mode switch on I2C? SDA/SCL swapped? Power on 3.3 V? |
| `0x3C` | SSD1306 OLED | Some clones use `0x3D` — a hardware deviation; update HDD-003 then `board.py` |
| `0x68` | DS3231 RTC | VCC/GND orientation; module seated |

For the full functional pass (grant/deny, auto-toggle, fail-closed SD test, power-cycle
persistence) and the troubleshooting table, see
[sen-TapIn_Wiring_and_Setup.pdf](sen-TapIn_Wiring_and_Setup.pdf) §8–§10.
