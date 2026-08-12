# main.py — sen-TapIn v0.1.0 (+mp)
# The state machine and start-up / fault handling (CS-003 §6).
#
# Deviation from CS-003 §6 / REQ-SPEC-003: the IN/OUT buttons are not
# fitted on this hardware, so the ARMED_IN/ARMED_OUT states are removed.
# The terminal is always listening; direction is auto-toggled per card
# (IN, then OUT, ...) from its last GRANTED log record, and the same
# card is ignored for DUP_SUPPRESS_MS (10 s) after a decided tap so one
# presentation cannot double-toggle. Record as a REQ/HDD/CS revision.

import time

from machine import I2C, Pin

import access
import board
import config
import nfc
import rtc
import sd_log
import ui

STATE_IDLE = "IDLE"
STATE_DECIDING = "DECIDING"
STATE_FEEDBACK = "FEEDBACK"
STATE_LOGGING = "LOGGING"
STATE_FAULT = "FAULT"

DIR_IN = "IN"
DIR_OUT = "OUT"
DIR_NONE = "-"          # denied taps have no toggle state

RESULT_GRANTED = "GRANTED"
RESULT_DENIED = "DENIED"

_relay = None


def _relay_level(on):
    if config.RELAY_ACTIVE_HIGH:
        return 1 if on else 0
    return 0 if on else 1


def _relay_init():
    # Fail-closed (REQ-S-003): the relay is de-energised before any other
    # subsystem starts, and doing nothing keeps it that way. v0.1.0 drives
    # an indicator LED only — never a lock or mains load (REQ-S-001).
    global _relay
    _relay = Pin(board.PIN_RELAY_LOCK, Pin.OUT, value=_relay_level(False))
    Pin(board.PIN_RELAY_SPARE, Pin.OUT, value=_relay_level(False))


def _relay_set(on):
    _relay.value(_relay_level(on))


def _startup(i2c):
    """Bring up every subsystem. Returns (ok, fault_message).

    If the SD card or the RTC (or any other peripheral) is unavailable,
    the terminal must not enter normal operation (REQ-NF-007).
    """
    if not ui.ui_init(i2c):
        return False, "OLED init"
    ui.ui_show_boot()
    if not rtc.rtc_init(i2c):
        return False, "RTC not found"
    if not nfc.nfc_init(i2c):
        return False, "NFC not found"
    if not sd_log.sd_init():
        return False, "SD card"
    if not sd_log.sd_ensure_allowlist():
        return False, "allow-list"
    return True, None


def _next_direction(directions, uid):
    """Auto-toggle: opposite of the card's last granted direction."""
    return DIR_OUT if directions.get(uid) == DIR_IN else DIR_IN


def _run():
    """Normal operation. Returns a fault message when it must stop."""
    # Toggle state is rebuilt from the log so it survives power cycles
    ok, directions = sd_log.sd_last_directions()
    if not ok:
        return "log read"

    state = STATE_IDLE
    uid = None
    granted = False
    name = ""
    direction = DIR_NONE
    last_tap = {}           # uid -> tick of its last decided tap
    next_refresh = time.ticks_ms()

    ui.ui_rgb(config.COLOR_IDLE)
    if not nfc.nfc_start_listen():
        return "NFC listen"

    while True:
        now = time.ticks_ms()

        if state == STATE_IDLE:
            if time.ticks_diff(now, next_refresh) >= 0:
                ok, ts = rtc.rtc_now()
                if not ok:
                    return "RTC read"
                ui.ui_show_idle(ts)  # REQ-F-009: clock + tap prompt
                next_refresh = time.ticks_add(now, config.IDLE_REFRESH_MS)
            ok, got = nfc.nfc_read_uid()
            if not ok:
                return "NFC read"
            if got is not None:
                uid = got
                state = STATE_DECIDING
            elif not nfc.nfc_is_listening():
                # poll ended with no target — start a fresh one
                if not nfc.nfc_start_listen():
                    return "NFC listen"

        elif state == STATE_DECIDING:
            tapped = last_tap.get(uid)
            if (tapped is not None
                    and time.ticks_diff(now, tapped) < config.DUP_SUPPRESS_MS):
                # 10 s same-card delay: ignore, do not toggle, do not log
                if not nfc.nfc_start_listen():
                    return "NFC listen"
                state = STATE_IDLE
                continue
            last_tap[uid] = now
            # Allow-list is read at decision time (HDD-003 §2.5) so edits
            # to the file apply without a restart
            ok, allowlist = sd_log.sd_read_allowlist()
            if not ok:
                return "allow-list read"
            granted, name = access.access_decide(uid, allowlist)  # REQ-F-004
            direction = _next_direction(directions, uid) if granted else DIR_NONE
            state = STATE_FEEDBACK

        elif state == STATE_FEEDBACK:
            # REQ-F-005 / REQ-NF-001: screen and colour change first, so the
            # user-visible result lands well inside the 1 s budget
            if granted:
                # direction-coded grant colour: IN green, OUT blue
                _relay_set(True)  # indicator LED pulse (REQ-S-001)
                ui.ui_anim_granted(name, direction,
                                   config.COLOR_GRANTED_IN if direction == DIR_IN
                                   else config.COLOR_GRANTED_OUT)
                _relay_set(False)
            else:
                # REQ-F-010: a denied result never actuates the relay
                ui.ui_anim_denied()
                print("DENIED uid:", uid)  # on serial for registration
            state = STATE_LOGGING

        elif state == STATE_LOGGING:
            ok, ts = rtc.rtc_now()  # REQ-F-007
            if not ok:
                return "RTC read"
            result = RESULT_GRANTED if granted else RESULT_DENIED
            if not sd_log.log_append(ts, uid, name, direction, result):
                # No silent log failures (CS-003 §5): a terminal that is not
                # recording must visibly stop (REQ-NF-003, REQ-NF-007)
                return "log write"
            if granted:
                # commit the toggle only once the record is on the card,
                # matching what sd_last_directions() would rebuild
                directions[uid] = direction
            time.sleep_ms(config.FEEDBACK_HOLD_MS)
            uid = None
            state = STATE_IDLE
            ui.ui_rgb(config.COLOR_IDLE)
            next_refresh = time.ticks_ms()
            if not nfc.nfc_start_listen():
                return "NFC listen"

        time.sleep_ms(config.TICK_MS)


def main():
    _relay_init()  # first action: reach the safe state (REQ-S-003)
    i2c = I2C(board.I2C_BUS_ID,
              sda=Pin(board.PIN_I2C_SDA),
              scl=Pin(board.PIN_I2C_SCL),
              freq=board.I2C_FREQ_HZ)
    while True:
        ok, message = _startup(i2c)
        if ok:
            message = _run()
        # STATE_FAULT (REQ-NF-007): show the cause, keep the relay
        # de-energised, and retry start-up until the fault clears
        _relay_set(False)
        nfc.nfc_abort()
        print("FAULT:", message)
        ui.ui_rgb(config.COLOR_FAULT)
        ui.ui_show_fault(message)
        time.sleep_ms(config.FAULT_RETRY_MS)


main()
