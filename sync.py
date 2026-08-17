# sync.py — sen-TapIn
# Roster check-in policy (CS-003 §2 addition): reads terminal.conf,
# decides when a check-in is due, fetches and parses the manifest, and
# reports what this terminal is running.
#
# SCOPE — THIS MODULE DOES NOT DOWNLOAD OR REPLACE THE ROSTER.
# It compares the local allow-list revision against the manifest and
# records the answer. Downloading, Ed25519 signature verification and
# the atomic swap are the next issue. Keeping those apart means a
# failure here is unambiguously a network or parsing failure, not a
# file-handling one.
#
# SECURITY ASSUMPTION for the download stage that follows: the security
# of roster sync rests entirely on the private signing key, which never
# leaves the build machine. Compromise of any terminal — including
# physical possession of its SD card — must not enable roster forgery.
# That is why the scheme is asymmetric: the terminal holds only a public
# key, which needs integrity but not secrecy.

import json
import time

import config
import net

_conf = None
_last_attempt = 0
_last_ok = None          # ticks of the last successful check-in
_last_ok_clock = None    # RTC timestamp of same, for the idle screen
_remote_rev = None


def sync_load_conf(path):
    """Read terminal.conf. Returns (ok, conf_dict).

    Format is 'key = value', one per line, '#' comments ignored. Kept
    on the SD card rather than in the repo so credentials are never
    committed, and so one identical firmware image runs on every
    terminal (config differs, firmware does not).

    A missing or unreadable file is not a fault — it means this terminal
    simply has no networking configured.
    """
    conf = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                conf[key.strip().lower()] = value.strip()
    except OSError:
        return False, {}
    return True, conf


def sync_init(conf):
    """Bring up networking from a loaded conf. Returns True/False.

    False means this terminal runs without networking for this session.
    The caller must treat that as normal operation, not a fault.
    """
    global _conf
    if not conf.get("ssid") or not conf.get("manifest_url"):
        print("sync: terminal.conf incomplete, networking disabled")
        return False
    if not net.net_init(conf.get("ssid"), conf.get("password", "")):
        return False
    _conf = conf
    return True


def sync_enabled():
    return _conf is not None


def sync_due(now, idle_since):
    """Is a check-in due, and is it safe to block for one right now?

    Two conditions, both required:

      * the poll interval (or the retry back-off after a failure) has
        elapsed, and
      * the terminal has been tap-free for SYNC_IDLE_GUARD_MS.

    The idle guard exists because net_http_get() blocks. The guard does
    not make the fetch instant — it makes it unlikely to land in the
    middle of somebody presenting a card. See the residual-risk note in
    the change description.
    """
    if _conf is None or not net.net_is_up():
        return False
    if time.ticks_diff(now, idle_since) < config.SYNC_IDLE_GUARD_MS:
        return False
    wait = config.SYNC_INTERVAL_MS if _last_ok is not None else config.SYNC_RETRY_MS
    if _last_attempt and time.ticks_diff(now, _last_attempt) < wait:
        return False
    return True


def sync_check_in(now, clock, local_rev, firmware):
    """Fetch the manifest and compare revisions. Returns (ok, detail).

    The check-in doubles as version reporting: the terminal's id,
    firmware and local revision go up as query parameters, so the
    server's ordinary access log answers "what is each terminal
    running?" without a second endpoint to build or maintain.

    Never raises. Any failure returns (False, reason) and the caller
    carries on with the roster already on the card.
    """
    global _last_attempt, _last_ok, _last_ok_clock, _remote_rev
    _last_attempt = now or 1
    url = "%s?id=%s&fw=%s&rev=%d" % (
        _conf["manifest_url"],
        _conf.get("terminal_id", "unknown"),
        firmware,
        local_rev,
    )
    ok, payload = net.net_http_get(url, config.HTTP_TIMEOUT_MS,
                                   config.HTTP_MAX_BODY)
    if not ok:
        print("sync: fetch failed:", payload)
        return False, payload
    ok, rev = _parse_manifest(payload)
    if not ok:
        print("sync: manifest parse failed")
        return False, "bad manifest"
    _last_ok = now or 1
    _last_ok_clock = clock
    _remote_rev = rev
    if rev > local_rev:
        return True, "rev %d available (local %d)" % (rev, local_rev)
    return True, "up to date (rev %d)" % local_rev


def sync_status_text(now):
    """Short line for the idle screen. 16 characters or fewer.

    Staleness is shown, not hidden. A terminal that has been offline for
    a day is still enforcing whatever roster it last had — including
    badges that have since been revoked — and it has no way to know it
    is wrong. Putting the age on the screen turns a silent failure into
    a visible one.
    """
    if _conf is None:
        return ""
    if _last_ok is None:
        return "sync never"
    age = time.ticks_diff(now, _last_ok)
    if age > config.SYNC_STALE_MS:
        return "sync ! %s" % _short_clock(_last_ok_clock)
    return "sync %s" % _short_clock(_last_ok_clock)


def sync_remote_rev():
    return _remote_rev


def _short_clock(timestamp):
    # timestamp is the rtc.rtc_now() string; take HH:MM
    if not timestamp or len(timestamp) < 16:
        return "?"
    return timestamp[11:16]


def _parse_manifest(payload):
    """Returns (ok, rev).

    Expected shape, with the fields the download stage will need
    already present so the format does not change under it:

        {"rev": 8,
         "url": "https://.../allowlist.txt",
         "sha256": "...",
         "sig": "..."}

    Only 'rev' is read here. Unknown fields are ignored rather than
    rejected, so the server can add fields without stranding terminals
    running older firmware.
    """
    try:
        doc = json.loads(payload)
        rev = int(doc["rev"])
    except (ValueError, KeyError, TypeError):
        return False, 0
    if rev < 0:
        return False, 0
    return True, rev
