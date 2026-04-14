#!/usr/bin/env python3
"""
Signs a ticket data payload with the machine's HMAC secret and
produces a valid QR code JSON for the Jackpot prize.
"""
import hmac
import hashlib
import json
import sys

SECRET = "3c0a8dfe0420367"
PRIZE  = "flag.txt"


def _sign(payload: str) -> str:
    return hmac.new(SECRET.encode(), payload.encode(),
                    hashlib.sha256).hexdigest()


def pack(data) -> str:
    if isinstance(data, str):
        data = json.loads(data)
    inner = json.dumps(data, separators=(", ", ": "))
    full = {"data": inner, "signature": _sign(inner), "prize": PRIZE}
    return json.dumps(full, separators=(", ", ": "))


if __name__ == "__main__":
    payload = sys.stdin.read().strip()
    print(pack(payload if payload else {}))
