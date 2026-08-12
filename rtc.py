# rtc.py — sen-TapIn v0.1.0 (+mp)
# DS3231 read/set over the shared I2C bus; returns timestamps for
# logging (REQ-F-007, REQ-NF-004). CS-003 §5: every function that can
# fail returns a status the caller must check.

import board

_REG_TIME = 0x00

_i2c = None


def _bcd2dec(value):
    return (value >> 4) * 10 + (value & 0x0F)


def _dec2bcd(value):
    return ((value // 10) << 4) | (value % 10)


def rtc_init(i2c):
    """Bind the bus and verify the DS3231 answers. Returns True/False."""
    global _i2c
    _i2c = i2c
    try:
        _i2c.readfrom_mem(board.I2C_ADDR_DS3231, _REG_TIME, 7)
    except OSError:
        return False
    return True


def rtc_now():
    """Read the RTC. Returns (ok, iso_timestamp).

    Timestamp is ISO 8601 (e.g. 2026-07-30T08:14:03) per the log schema
    in REQ-SPEC-003 §4.
    """
    try:
        raw = _i2c.readfrom_mem(board.I2C_ADDR_DS3231, _REG_TIME, 7)
    except OSError:
        return False, None
    second = _bcd2dec(raw[0] & 0x7F)
    minute = _bcd2dec(raw[1] & 0x7F)
    hour = _bcd2dec(raw[2] & 0x3F)  # DS3231 kept in 24-hour mode
    day = _bcd2dec(raw[4] & 0x3F)
    month = _bcd2dec(raw[5] & 0x1F)
    year = 2000 + _bcd2dec(raw[6])
    return True, "%04d-%02d-%02dT%02d:%02d:%02d" % (
        year, month, day, hour, minute, second)


def rtc_set(year, month, day, hour, minute, second):
    """Set the RTC (bring-up helper, run from the REPL). Returns True/False.

    Example:  import rtc; rtc.rtc_set(2026, 7, 30, 9, 41, 0)
    (call rtc_init(i2c) first if running standalone).
    """
    data = bytes((
        _dec2bcd(second),
        _dec2bcd(minute),
        _dec2bcd(hour),          # bit 6 clear = 24-hour mode
        1,                       # day-of-week unused by sen-TapIn
        _dec2bcd(day),
        _dec2bcd(month),         # century bit clear: years 2000-2099
        _dec2bcd(year - 2000),
    ))
    try:
        _i2c.writeto_mem(board.I2C_ADDR_DS3231, _REG_TIME, data)
    except OSError:
        return False
    return True
