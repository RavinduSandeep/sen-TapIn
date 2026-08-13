# access.py — sen-TapIn
# Allow-list lookup and the grant/deny decision (REQ-F-004, REQ-F-010).


def access_decide(uid_hex, allowlist):
    """Decide authorisation for a card UID. Returns (granted, name).

    SECURITY — REQ-S-002 / HDD REQ-HW-002 (mandatory notice, CS-003 §8):
    UID-based authorisation is NOT secure. A card UID is transmitted in
    the clear and is trivially cloneable, so this decision must not be
    treated as a real access-control mechanism. sen-TapIn is a learning
    and attendance baseline; the planned hardening stage replaces this
    with a protected-sector secret, challenge-response, or a second
    factor.
    """
    name = allowlist.get(uid_hex)
    if name is None:
        # REQ-F-010: unknown card -> denied, logged with name "unknown"
        return False, "unknown"
    return True, name
