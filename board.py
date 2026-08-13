# board.py — sen-TapIn
# Single source of the frozen pin map and I2C addresses from HDD-003 §3.
# CS-003 §3: every pin number and bus address is declared exactly once,
# here, and referenced nowhere else by literal value (REQ-NF-005 /
# HDD REQ-HW-001). No logic in this file.
#
# Pin references are Pico 2 W GPIO numbers (GPn); the physical pin
# number from HDD-003 is noted alongside.

# --- I2C0 shared bus: DS3231 + SSD1306 + PN532 (HDD-003 §3.1) ---
I2C_BUS_ID = 0
PIN_I2C_SDA = 4          # GP4  (physical pin 6)
PIN_I2C_SCL = 5          # GP5  (physical pin 7)
I2C_FREQ_HZ = 400_000

I2C_ADDR_DS3231 = 0x68   # battery-backed RTC
I2C_ADDR_SSD1306 = 0x3C  # 128x64 OLED
I2C_ADDR_PN532 = 0x24    # NFC reader (module mode selector set to I2C)

OLED_WIDTH = 128
OLED_HEIGHT = 64

# --- SPI0 dedicated bus: MicroSD module (HDD-003 §3.2) ---
SPI_BUS_ID = 0
PIN_SPI_SCK = 18         # GP18 (physical pin 24)
PIN_SPI_MOSI = 19        # GP19 (physical pin 25)
PIN_SPI_MISO = 16        # GP16 (physical pin 21)
PIN_SD_CS = 17           # GP17 (physical pin 22)

# --- GPIO actuators and feedback (HDD-003 §3.3) ---
PIN_RELAY_LOCK = 10      # GP10 (physical pin 14) — indicator LED in v0.1.0
PIN_RELAY_SPARE = 11     # GP11 (physical pin 15) — reserved, parked off
PIN_WS2811_DATA = 12     # GP12 (physical pin 16) — timed single-wire serial
PIN_BUZZER = 15          # GP15 (physical pin 20) — active low-trigger module
                         # (see config.BUZZER_LOW_TRIGGER deviation note)

# Deviation from HDD-003 Rev 1.0 §3.3: the IN/OUT mode buttons (GP13,
# GP14) are not fitted — direction is auto-toggled per card instead.
# GP13 and GP14 are unallocated; record this as an HDD-003 revision.
