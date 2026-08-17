# config.py — sen-TapIn
# Tunable configuration constants (CS-003 §9), kept separate from the
# pin map in board.py so configuration and wiring do not mix.
# Timing defaults come from REQ-SPEC-003 §6 and may be tuned during
# bring-up by editing the named constant only; note any change.
# (config.py is an addition to the CS-003 §2 module list: CS-003 §9
# requires these constants grouped by purpose outside the pin map.)

# --- Timing ---
# Deviation from REQ-SPEC-003 (two-button explicit mode): this build is
# always listening and auto-toggles direction per card. The suppression
# window below is the "10 s delay" — the same card is ignored for 10 s
# after a decided tap, so one presentation cannot double-toggle.
DUP_SUPPRESS_MS = 10_000      # same-card delay between decided taps
TICK_MS = 20                  # main loop tick
IDLE_REFRESH_MS = 1_000       # OLED clock / countdown refresh
RELAY_PULSE_MS = 600          # relay (indicator LED) pulse on grant
FEEDBACK_HOLD_MS = 1_200      # how long the result screen stays up
FAULT_RETRY_MS = 5_000        # re-attempt start-up while faulted (REQ-NF-007)

# --- Relay polarity ---
# Many opto-isolated relay boards are active-LOW. Verify during bring-up
# and flip this constant if the relay clicks on at boot.
RELAY_ACTIVE_HIGH = True

# --- WS2811 RGB (colours are (R, G, B), 0-255) ---
WS2811_COUNT = 1
WS2811_ORDER = "GRB"          # fitted module verified GRB (WS2812-style) at
                              # bring-up: red/green were swapped with "RGB"
WS2811_TIMING = 1             # 1 = 800 kHz; set 0 if the module is a 400 kHz part
COLOR_OFF = (0, 0, 0)
COLOR_IDLE = (0, 0, 0)        # LED off while idle (deviation from HDD-003 §2.6
                              # gentle idle tint — off preferred at bring-up)
COLOR_GRANTED_IN = (0, 80, 0)   # REQ-F-005: green on grant, direction IN
COLOR_GRANTED_OUT = (0, 0, 80)  # grant, direction OUT (blue; REQ-F-005 deviation:
                                # direction-coded grant colour requested at bring-up)
COLOR_DENIED = (80, 0, 0)     # REQ-F-005: red on deny
COLOR_FAULT = (60, 12, 0)

# --- Feedback animations (bring-up addition; see ui.py) ---
# Big-text result animations: slide-in WELCOME/GOODBYE on grant, shake +
# invert flash on deny, with the RGB LED ramping/pulsing in sync. Kept
# short so tap-to-feedback stays inside the 1 s budget (REQ-NF-001):
# the first animation frame is on screen within one frame time.
ANIM_SLIDE_STEPS = 10         # frames for the big-text slide-in
ANIM_PULSE_FRAMES = 6         # chevron/pulse frames after the slide
ANIM_PULSE_MS = 110           # delay per pulse frame

# --- Buzzer tones: sequences of (frequency Hz, duration ms) ---
# Deviation from HDD-003 §3.3 (passive buzzer, PWM): the fitted module
# is an ACTIVE buzzer with a LOW-level trigger (3-pin VCC/IO/GND).
# IO LOW = sound, IO HIGH = silent, fixed tone. With the flag below set
# the frequency values in the tone tables are ignored and only the
# duration pattern plays. Record as an HDD-003 revision.
BUZZER_LOW_TRIGGER = True     # False = passive buzzer on PWM, per HDD-003
BUZZER_DUTY = 32768           # 50% PWM duty (passive buzzer only)
TONE_GAP_MS = 25
TONE_GRANT = ((1047, 120), (1568, 180))   # rising confirmation (REQ-F-005)
TONE_DENY = ((392, 180), (262, 320))      # falling error tone (REQ-F-005)

# --- Files (SD card) ---
SD_MOUNT = "/sd"
ALLOWLIST_PATH = "/sd/allowlist.txt"      # REQ-F-008: human-readable UID,Name
LOG_PATH = "/sd/attendance.csv"           # REQ-F-006: append-only event log
LOG_HEADER = "timestamp,uid,name,direction,result\n"  # REQ-SPEC-003 §4 schema

# Diagnostic log, separate from the attendance record above. Not part of
# the REQ-SPEC-003 §4 schema and deliberately NOT fail-closed: a write
# failure here is printed to serial and ignored, so an unwritable or full
# card can never stop the terminal deciding and logging attendance.
EVENTS_PATH = "/sd/events.log"


# Association is incremental (net.net_tick), so this timeout bounds an
# attempt, not a blocking wait.
WIFI_CONNECT_TIMEOUT_MS = 15_000
WIFI_RETRY_MS = 30_000        # back-off after a failed association

# net.net_http_get() BLOCKS for up to this long. It is gated behind the
# idle guard below so it cannot easily land mid-tap. Keep it short: this
# is the one place networking can delay a card read (REQ-NF-001).
HTTP_TIMEOUT_MS = 2_000
HTTP_MAX_BODY = 2_048         # memory guard on the manifest response

SYNC_INTERVAL_MS = 900_000    # 15 min between successful check-ins
SYNC_RETRY_MS = 60_000        # sooner retry after a failure
SYNC_IDLE_GUARD_MS = 3_000    # terminal must be tap-free this long first
SYNC_STALE_MS = 86_400_000    # 24 h; older than this is flagged on screen