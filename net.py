# net.py — sen-TapIn
# Wi-Fi association and plain HTTP(S) GET (CS-003 §2 addition).
#
# TWO RULES GOVERN EVERYTHING IN THIS MODULE:
#
#   1. Nothing here may ever fault the terminal. Every function returns
#      a status; none raises. The network is an optional convenience —
#      a dead router, a wrong password or a missing access point must
#      leave the terminal granting, denying and logging exactly as it
#      did before Wi-Fi existed. net_* functions are deliberately NOT
#      called from main._startup(), so they cannot enter the fault
#      chain (REQ-NF-007).
#
#   2. Association is incremental, never blocking. net_tick() is called
#      once per main-loop pass and returns immediately; it never waits
#      for a connection. Only net_http_get() blocks, and main.py gates
#      that behind an idle guard — see config.SYNC_IDLE_GUARD_MS and the
#      note in sync.py.

import time

try:
    import network
    import socket
except ImportError:      # pragma: no cover - host-side testing only
    network = None
    socket = None

try:
    import ssl
except ImportError:
    ssl = None

import config

STATE_OFF = "OFF"
STATE_CONNECTING = "CONNECTING"
STATE_UP = "UP"

_wlan = None
_state = STATE_OFF
_started = 0
_next_attempt = 0
_ssid = None
_password = None


def net_init(ssid, password):
    """Prepare the interface. Returns True/False, never raises.

    Called once, after the card is mounted and terminal.conf is read.
    A False return means networking is unavailable for this session and
    the caller carries on without it.
    """
    global _wlan, _ssid, _password, _state
    if network is None:
        print("net: no network module on this build")
        return False
    if not ssid:
        print("net: no ssid configured")
        return False
    try:
        _wlan = network.WLAN(network.STA_IF)
        _wlan.active(True)
    except Exception as e:
        # bare Exception is deliberate: an unusable radio must degrade
        # to "no networking", never propagate out of this module
        print("net: interface init failed:", repr(e))
        _wlan = None
        return False
    _ssid = ssid
    _password = password
    _state = STATE_OFF
    return True


def net_tick(now):
    """Drive association forward. Returns the current state.

    Returns immediately every time. Safe to call on every main-loop
    pass; the terminal must never wait on this.
    """
    global _state, _started, _next_attempt
    if _wlan is None:
        return STATE_OFF

    if _state == STATE_UP:
        if not _is_up():
            print("net: association lost")
            _state = STATE_OFF
            _next_attempt = time.ticks_add(now, config.WIFI_RETRY_MS)
        return _state

    if _state == STATE_CONNECTING:
        if _is_up():
            print("net: up as", _ifaddr())
            _state = STATE_UP
        elif time.ticks_diff(now, _started) > config.WIFI_CONNECT_TIMEOUT_MS:
            print("net: association timed out")
            _abort()
            _state = STATE_OFF
            _next_attempt = time.ticks_add(now, config.WIFI_RETRY_MS)
        return _state

    # STATE_OFF — start a fresh attempt once the back-off has expired
    if time.ticks_diff(now, _next_attempt) < 0:
        return _state
    try:
        _wlan.connect(_ssid, _password)
    except Exception as e:
        print("net: connect failed:", repr(e))
        _next_attempt = time.ticks_add(now, config.WIFI_RETRY_MS)
        return _state
    _started = now
    _state = STATE_CONNECTING
    return _state


def net_is_up():
    return _state == STATE_UP and _is_up()


def net_http_get(url, timeout_ms, max_bytes):
    """Fetch a URL. Returns (ok, body_bytes_or_message).

    BLOCKING, up to roughly timeout_ms. The caller is responsible for
    only calling this when a pause is acceptable — main.py gates it on
    the terminal having been tap-free for config.SYNC_IDLE_GUARD_MS.

    Deliberately minimal: no redirects, no chunked transfer-encoding,
    no keep-alive. The manifest is a small static file on a host we
    control; anything more elaborate is a liability on a device whose
    real job is answering card taps.
    """
    if socket is None:
        return False, "no socket module"
    try:
        scheme, host, port, path = _split_url(url)
    except ValueError as e:
        return False, str(e)
    if scheme == "https" and ssl is None:
        return False, "no ssl module in this build"

    sock = None
    try:
        addr = socket.getaddrinfo(host, port)[0][-1]
        sock = socket.socket()
        sock.settimeout(timeout_ms / 1000)
        sock.connect(addr)
        if scheme == "https":
            # Certificate validation is the caller's security decision,
            # not this module's; see the note in sync.py on why the
            # Ed25519 signature — not the transport — is the control
            # that matters for roster authenticity.
            sock = ssl.wrap_socket(sock, server_hostname=host)
        request = (
            "GET %s HTTP/1.0\r\n"
            "Host: %s\r\n"
            "User-Agent: sen-TapIn\r\n"
            "Connection: close\r\n\r\n" % (path, host)
        )
        sock.write(request.encode())
        raw = _read_capped(sock, max_bytes)
    except Exception as e:
        # OSError covers timeouts and refusals; ssl and DNS failures
        # raise other types. None of them may escape this module.
        return False, repr(e)
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass

    return _split_response(raw)


def net_down():
    """Drop the association. Used when networking is disabled or the
    terminal is shutting a session down. Never raises."""
    global _state
    _abort()
    _state = STATE_OFF


# --- internals ---

def _is_up():
    try:
        return bool(_wlan.isconnected())
    except Exception:
        return False


def _ifaddr():
    try:
        return _wlan.ifconfig()[0]
    except Exception:
        return "?"


def _abort():
    if _wlan is None:
        return
    try:
        _wlan.disconnect()
    except Exception:
        pass


def _split_url(url):
    """'https://host:443/a/b' -> ('https', 'host', 443, '/a/b')."""
    if url.startswith("https://"):
        scheme, rest = "https", url[8:]
        port = 443
    elif url.startswith("http://"):
        scheme, rest = "http", url[7:]
        port = 80
    else:
        raise ValueError("url must start with http:// or https://")
    slash = rest.find("/")
    if slash < 0:
        hostport, path = rest, "/"
    else:
        hostport, path = rest[:slash], rest[slash:]
    if ":" in hostport:
        host, _, port_text = hostport.partition(":")
        try:
            port = int(port_text)
        except ValueError:
            raise ValueError("bad port in url")
    else:
        host = hostport
    if not host:
        raise ValueError("no host in url")
    return scheme, host, port, path


def _read_capped(sock, max_bytes):
    """Read until close or the cap. The cap is a memory guard: a
    misconfigured URL pointing at something large must not exhaust RAM
    on a 520 KB device."""
    chunks = []
    total = 0
    while total < max_bytes:
        block = sock.read(256)
        if not block:
            break
        chunks.append(block)
        total += len(block)
    return b"".join(chunks)


def _split_response(raw):
    """Return (ok, body) for a 200, else (False, message)."""
    if not raw:
        return False, "empty response"
    head, _, body = raw.partition(b"\r\n\r\n")
    first = head.split(b"\r\n")[0].decode()
    parts = first.split(" ")
    if len(parts) < 2:
        return False, "malformed status line"
    if parts[1] != "200":
        return False, "http %s" % parts[1]
    return True, body
