# nfc.py — sen-TapIn
# PN532 (DFRobot Gravity DFR0231-H) UID read over I2C (REQ-F-001).
# The module's mode selector must be set to I2C (HDD-003 §2.2).
#
# This is a minimal driver: only the three PN532 commands this product
# needs. Card polling is split into nfc_start_listen() (issues the
# command) and nfc_read_uid() (non-blocking check), so no state handler
# blocks while waiting for a card (CS-003 §6, REQ-NF-001).

import time

import board

_CMD_GET_FIRMWARE_VERSION = 0x02
_CMD_SAM_CONFIGURATION = 0x14
_CMD_IN_LIST_PASSIVE_TARGET = 0x4A

_TFI_HOST = 0xD4      # frame identifier: host -> PN532
_TFI_PN532 = 0xD5     # frame identifier: PN532 -> host

_ACK = b"\x00\x00\xff\x00\xff\x00"
_BAUD_ISO14443A = 0x00

_ACK_WAIT_MS = 100
_RESP_WAIT_MS = 400

_i2c = None
_listening = False


def _write_frame(body):
    length = len(body) + 1  # body plus TFI byte
    frame = bytearray(len(body) + 8)
    frame[0] = 0x00                      # preamble
    frame[1] = 0x00                      # start code
    frame[2] = 0xFF
    frame[3] = length
    frame[4] = (0x100 - length) & 0xFF   # length checksum
    frame[5] = _TFI_HOST
    frame[6:6 + len(body)] = bytes(body)
    frame[-2] = (0x100 - ((_TFI_HOST + sum(body)) & 0xFF)) & 0xFF
    frame[-1] = 0x00                     # postamble
    try:
        _i2c.writeto(board.I2C_ADDR_PN532, frame)
    except OSError:
        return False
    return True


def _ready():
    # In I2C mode the PN532 prepends a status byte to every read;
    # bit 0 set means a frame is waiting.
    try:
        return _i2c.readfrom(board.I2C_ADDR_PN532, 1)[0] & 0x01 == 0x01
    except OSError:
        return False


def _wait_ready(timeout_ms):
    deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        if _ready():
            return True
        time.sleep_ms(2)
    return False


def _read_ack():
    try:
        raw = _i2c.readfrom(board.I2C_ADDR_PN532, 7)
    except OSError:
        return False
    return raw[1:7] == _ACK


def _read_response(command):
    """Read one response frame. Returns the body after the TFI byte
    ([response_code, data...]) or None on any framing/bus error."""
    try:
        raw = _i2c.readfrom(board.I2C_ADDR_PN532, 64)
    except OSError:
        return None
    buf = raw[1:]  # skip the I2C status byte
    start = -1
    for i in range(len(buf) - 1):
        if buf[i] == 0x00 and buf[i + 1] == 0xFF:
            start = i + 2
            break
    if start < 0 or start + 2 > len(buf):
        return None
    length = buf[start]
    lcs = buf[start + 1]
    if (length + lcs) & 0xFF != 0x00:
        return None
    body = bytes(buf[start + 2:start + 2 + length])
    if len(body) != length or length < 2:
        return None
    if body[0] != _TFI_PN532 or body[1] != command + 1:
        return None
    return body[1:]


def _call(body, resp_wait_ms=_RESP_WAIT_MS):
    if not _write_frame(body):
        return None
    if not _wait_ready(_ACK_WAIT_MS) or not _read_ack():
        return None
    if not _wait_ready(resp_wait_ms):
        return None
    return _read_response(body[0])


def nfc_init(i2c):
    """Verify the PN532 responds and put it in normal mode. True/False."""
    global _i2c, _listening
    _i2c = i2c
    _listening = False
    if _call([_CMD_GET_FIRMWARE_VERSION]) is None:
        return False
    # SAMConfiguration: normal mode, default timeout, IRQ pin unused
    return _call([_CMD_SAM_CONFIGURATION, 0x01, 0x14, 0x00]) is not None


def nfc_start_listen():
    """Start a passive poll for one ISO 14443A card. Returns True/False.

    The PN532 holds the command open until a card arrives; collect the
    result with nfc_read_uid() and cancel with nfc_abort().
    """
    global _listening
    if _listening:
        nfc_abort()
    if not _write_frame([_CMD_IN_LIST_PASSIVE_TARGET, 0x01, _BAUD_ISO14443A]):
        return False
    if not _wait_ready(_ACK_WAIT_MS) or not _read_ack():
        return False
    _listening = True
    return True


def nfc_is_listening():
    return _listening


def nfc_read_uid():
    """Non-blocking poll check. Returns (ok, uid_hex).

    ok False   -> bus/framing fault (caller must treat as a fault)
    uid None   -> no card yet (or poll ended with no target)
    uid string -> card UID in uppercase hex (REQ-F-001)
    """
    global _listening
    if not _listening or not _ready():
        return True, None
    body = _read_response(_CMD_IN_LIST_PASSIVE_TARGET)
    _listening = False
    if body is None:
        return False, None
    # body: [0x4B, NbTg, Tg, SENS_RES(2), SEL_RES, uid_len, uid...]
    if len(body) < 2 or body[1] == 0:
        return True, None
    if len(body) < 8:
        return False, None
    uid_len = body[6]
    uid = body[7:7 + uid_len]
    if len(uid) != uid_len:
        return False, None
    return True, "".join("%02X" % b for b in uid)


def nfc_abort():
    """Cancel an outstanding poll (a host ACK aborts the running command)."""
    global _listening
    if _i2c is not None:
        try:
            _i2c.writeto(board.I2C_ADDR_PN532, _ACK)
        except OSError:
            pass
    _listening = False
