# 2sd_log.py — sen-TapIn v0.1.0 (+mp)
# SD mount, allow-list read, append-only attendance log
# (REQ-F-006, REQ-F-008, REQ-NF-003). CS-003 §7: the log is written by
# the single function log_append() so the record format cannot drift.

import os

from machine import Pin, SPI

import board
import config
from sdcard import SDCard

_ALLOWLIST_TEMPLATE = (
    "# sen-TapIn allow-list (REQ-F-008)\n"
    "# One card per line:  UID,Name\n"
    "# UID is uppercase hex with no separators, e.g. 04A2B3C4\n"
    "# Names must not contain commas. Lines starting with # are ignored.\n"
    "# Example:\n"
    "# 04A2B3C4,R. Madanayaka\n"
)

_mounted = False


def sd_init():
    """Mount the SD card on the dedicated SPI bus. Returns True/False."""
    global _mounted
    try:
        os.umount(config.SD_MOUNT)  # clear a stale mount after a fault retry
    except OSError:
        pass
    _mounted = False
    try:
        spi = SPI(
            board.SPI_BUS_ID,
            sck=Pin(board.PIN_SPI_SCK),
            mosi=Pin(board.PIN_SPI_MOSI),
            miso=Pin(board.PIN_SPI_MISO),
        )
        sd = SDCard(spi, Pin(board.PIN_SD_CS))
    except OSError as e:
        # card-level failure: wiring, power, or no card present
        print("SD init failed (card):", repr(e))
        return False
    try:
        os.mount(sd, config.SD_MOUNT)
    except OSError as e:
        # mount-level failure: usually not FAT32 / unreadable filesystem
        print("SD init failed (mount):", repr(e))
        return False
    _mounted = True
    return True


def _exists(path):
    try:
        os.stat(path)
    except OSError:
        return False
    return True


def sd_ensure_allowlist():
    """Create a commented allow-list template if none exists. True/False."""
    if not _mounted:
        return False
    if _exists(config.ALLOWLIST_PATH):
        return True
    try:
        with open(config.ALLOWLIST_PATH, "w") as f:
            f.write(_ALLOWLIST_TEMPLATE)
        _sync()
    except OSError:
        return False
    return True


def sd_read_allowlist():
    """Read the allow-list. Returns (ok, {uid_hex: name}).

    Read fresh at decision time (HDD-003 §2.5) so edits to the file take
    effect without a restart.
    """
    if not _mounted:
        return False, None
    table = {}
    try:
        with open(config.ALLOWLIST_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "," not in line:
                    continue
                uid, name = line.split(",", 1)
                table[uid.strip().upper()] = name.strip()
    except OSError:
        return False, None
    return True, table


def _directions_from_lines(lines):
    """Pure helper: last GRANTED direction per UID from log lines."""
    table = {}
    for line in lines:
        fields = line.strip().split(",")
        # schema: timestamp,uid,name,direction,result (REQ-SPEC-003 §4)
        if len(fields) < 5 or fields[4] != "GRANTED":
            continue
        if fields[3] in ("IN", "OUT"):
            table[fields[1]] = fields[3]
    return table


def sd_last_directions():
    """Rebuild {uid: last granted direction} from the log. (ok, dict).

    The log itself is the single source of the auto-toggle state, so
    direction survives a power cycle without a separate state file.
    A missing log file is a valid empty state, not a fault.
    """
    if not _mounted:
        return False, None
    if not _exists(config.LOG_PATH):
        return True, {}
    try:
        with open(config.LOG_PATH) as f:
            return True, _directions_from_lines(f)
    except OSError:
        return False, None


def log_append(timestamp, uid, name, direction, result):
    """Append one attendance record and flush it. Returns True/False.

    Writes exactly the REQ-SPEC-003 §4 schema. Open/append/flush/close
    per record so a power loss costs at most the in-progress record
    (REQ-NF-003). The caller must treat False as a fault — a log-write
    failure is never ignored (CS-003 §5).
    """
    if not _mounted:
        return False
    record = "%s,%s,%s,%s,%s\n" % (timestamp, uid, name, direction, result)
    try:
        write_header = not _exists(config.LOG_PATH)
        with open(config.LOG_PATH, "a") as f:
            if write_header:
                f.write(config.LOG_HEADER)
            f.write(record)
            f.flush()
        _sync()
    except OSError:
        return False
    return True


def _sync():
    if hasattr(os, "sync"):
        os.sync()

