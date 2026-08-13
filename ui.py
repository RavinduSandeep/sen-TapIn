# ui.py — sen-TapIn
# OLED, WS2811 RGB, and buzzer feedback (CS-003 §2).
# All draw/colour/tone values come from named constants in config.py;
# nothing here decides anything — main.py owns the state machine.

import time

import framebuf
import neopixel
from machine import Pin, PWM

import board
import config
from ssd1306 import SSD1306_I2C

_oled = None
_np = None
_buzzer = None


def ui_init(i2c):
    """Bring up OLED, RGB and buzzer. Returns True/False."""
    global _oled, _np, _buzzer
    try:
        _oled = SSD1306_I2C(board.OLED_WIDTH, board.OLED_HEIGHT, i2c,
                            addr=board.I2C_ADDR_SSD1306)
    except OSError:
        _oled = None
        return False
    # WS2811 driven by machine.bitstream under neopixel (HDD-003 §4)
    _np = neopixel.NeoPixel(Pin(board.PIN_WS2811_DATA),
                            config.WS2811_COUNT,
                            timing=config.WS2811_TIMING)
    if config.BUZZER_LOW_TRIGGER:
        # active low-trigger module: drive HIGH immediately so it is
        # silent from the first moment the pin leaves its reset state
        _buzzer = Pin(board.PIN_BUZZER, Pin.OUT, value=1)
    else:
        _buzzer = PWM(Pin(board.PIN_BUZZER))
        _buzzer.duty_u16(0)
    ui_rgb(config.COLOR_OFF)
    return True


def ui_rgb(color):
    """Set the WS2811 to an (R, G, B) colour."""
    if _np is None:
        return
    r, g, b = color
    if config.WS2811_ORDER == "RGB":
        # neopixel emits GRB wire order (WS2812); swap so an RGB-order
        # WS2811 shows the intended colour
        _np[0] = (g, r, b)
    else:
        _np[0] = (r, g, b)
    _np.write()


def ui_play(tone_seq):
    """Play a ((freq_hz, duration_ms), ...) sequence on the buzzer.

    Blocking, but sequences are short by design so tap-to-feedback stays
    inside the 1 s budget (REQ-NF-001).
    """
    if _buzzer is None:
        return
    for freq, ms in tone_seq:
        if config.BUZZER_LOW_TRIGGER:
            # active buzzer: fixed tone, freq ignored — beep for ms
            _buzzer.value(0)
            time.sleep_ms(ms)
            _buzzer.value(1)
        else:
            _buzzer.freq(freq)
            _buzzer.duty_u16(config.BUZZER_DUTY)
            time.sleep_ms(ms)
            _buzzer.duty_u16(0)
        time.sleep_ms(config.TONE_GAP_MS)


def _rgb_dim(color, level):
    """Scale an (R, G, B) colour to level/255 brightness."""
    r, g, b = color
    return (r * level // 255, g * level // 255, b * level // 255)


def _big_text(text, x, y, scale):
    """Draw text scaled up from the built-in 8x8 font (scale 2 = 16 px)."""
    if _oled is None:
        return
    w = 8 * len(text)
    tmp = framebuf.FrameBuffer(bytearray(w), w, 8, framebuf.MONO_HLSB)
    tmp.text(text, 0, 0, 1)
    for py in range(8):
        for px in range(w):
            if tmp.pixel(px, py):
                _oled.fill_rect(x + px * scale, y + py * scale,
                                scale, scale, 1)


def _anim_slide_in(msg, color):
    """Big-text slide-in from the left with the LED ramping up in step.
    Shared by every result animation so all three scenarios move the
    same way (bring-up request)."""
    target_x = (board.OLED_WIDTH - 16 * len(msg)) // 2
    steps = config.ANIM_SLIDE_STEPS
    for step in range(1, steps + 1):
        x = -16 * len(msg) + (target_x + 16 * len(msg)) * step // steps
        _oled.fill(0)
        _big_text(msg, x, 8, 2)
        _oled.show()
        ui_rgb(_rgb_dim(color, 255 * step // steps))


def _anim_pulse(lines, color):
    """Lower-half detail text with a gentle LED pulse. lines is an
    iterable of (x, y, text) per frame index i."""
    for i in range(config.ANIM_PULSE_FRAMES):
        _oled.fill_rect(0, 32, board.OLED_WIDTH, 32, 0)
        for x, y, text in lines(i):
            _oled.text(text, x, y)
        _oled.show()
        ui_rgb(_rgb_dim(color, 255 if i % 2 == 0 else 120))
        time.sleep_ms(config.ANIM_PULSE_MS)
    ui_rgb(color)


def ui_anim_granted(name, direction, color):
    """Grant feedback: big WELCOME (IN) / GOODBYE (OUT) slides in while
    the LED ramps up, the grant tone plays, then the name is shown with
    marching direction chevrons and a gentle LED pulse. Blocking, but
    the first frame lands immediately (REQ-NF-001)."""
    if _oled is None:
        ui_rgb(color)
        return
    _anim_slide_in("WELCOME" if direction == "IN" else "GOODBYE", color)
    ui_play(config.TONE_GRANT)
    chev = ">" if direction == "IN" else "<"
    _anim_pulse(lambda i: ((0, 38, name[:16]),
                           (0, 54, "%s %s" % (direction, chev * (i % 3 + 1)))),
                color)


def ui_anim_denied():
    """Deny feedback: big DENIED slides in exactly like the grant
    animation, but with the LED ramping red, then the deny tone and a
    red pulse over the reason text."""
    if _oled is None:
        ui_rgb(config.COLOR_DENIED)
        return
    _anim_slide_in("DENIED", config.COLOR_DENIED)
    ui_play(config.TONE_DENY)
    _anim_pulse(lambda i: ((32, 38, "Card not"),
                           (24, 52, "authorised")),
                config.COLOR_DENIED)


def _screen(lines):
    """lines: iterable of (x, y, text)."""
    if _oled is None:
        return
    _oled.fill(0)
    for x, y, text in lines:
        _oled.text(text, x, y)
    _oled.show()


def ui_show_boot(version_text, rev=None):
    """Boot screen. version_text comes from main.py (version.py is the
    single source); rev is the allow-list revision, or None before the
    card is mounted and it is not yet known.

    Both strings fit the 16-character line width of the 8 px font.
    """
    lines = [
        (0, 8, "sen-TapIn"),
        (0, 24, version_text),
    ]
    if rev is not None:
        lines.append((0, 40, "roster rev %d" % rev))
    lines.append((0, 56, "starting..."))
    _screen(lines)


def ui_show_idle(timestamp):
    # REQ-F-009: idle shows RTC time and the tap prompt (always listening)
    _screen((
        (0, 0, "sen-TapIn"),
        (0, 20, timestamp[11:19]),   # HH:MM:SS
        (0, 32, timestamp[0:10]),    # YYYY-MM-DD
        (0, 52, "Tap your card"),
    ))


def ui_show_granted(name, direction):
    # auto-toggle: the resolved direction is shown with the result
    _screen((
        (0, 8, "GRANTED  %s" % direction),
        (0, 28, name[:16]),
        (0, 38, name[16:32]),
    ))


def ui_show_denied():
    # UID is deliberately not displayed (bring-up request); it still goes
    # to the serial console and the log for allow-list registration
    _screen((
        (0, 8, "DENIED"),
        (0, 28, "Card not"),
        (0, 38, "authorised"),
    ))


def ui_show_fault(message):
    # REQ-NF-007: faults are displayed and normal operation is blocked
    _screen((
        (0, 0, "FAULT"),
        (0, 20, message[:16]),
        (0, 30, message[16:32]),
        (0, 52, "retrying..."),
    ))
