"""India identity & bank validators — pure, deterministic, no I/O.

Each `validate_*` normalises its input (trim + uppercase where applicable) and
returns the canonical form, or raises `ValueError` with a human-readable
message. Use them in Pydantic field validators at the API boundary so bad PII
never reaches the shared ONAQT tables.

References:
- PAN: 10 chars `AAAAA9999A` — 5 letters, 4 digits, 1 letter; 4th char is the
  holder type (P=individual, C=company, H=HUF, F=firm, ...).
- Aadhaar: 12 digits, last digit a Verhoeff checksum; cannot start with 0 or 1.
- IFSC: 11 chars `AAAA0XXXXXX` — 4 bank letters, a reserved '0', 6 alnum branch.
- UAN: 12 digits (EPFO universal account number).
"""

import re

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
PAN_TYPE_CHARS = set("ABCFGHLJPT")  # valid 4th-char holder types
IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")

# Verhoeff multiplication (d), permutation (p) and inverse tables.
_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)


def _verhoeff_check(digits: str) -> bool:
    """True when `digits` (incl. its trailing check digit) is Verhoeff-valid."""
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(ch)]]
    return c == 0


def validate_pan(value: str) -> str:
    pan = value.strip().upper()
    if not PAN_RE.match(pan):
        raise ValueError(
            "PAN must be 10 characters: 5 letters, 4 digits, 1 letter (e.g. ABCPE1234F)"
        )
    if pan[3] not in PAN_TYPE_CHARS:
        raise ValueError(f"PAN holder-type letter '{pan[3]}' (4th char) is not valid")
    return pan


def validate_aadhaar(value: str) -> str:
    raw = re.sub(r"[\s-]", "", value.strip())
    if not (len(raw) == 12 and raw.isdigit()):
        raise ValueError("Aadhaar must be 12 digits")
    if raw[0] in "01":
        raise ValueError("Aadhaar cannot start with 0 or 1")
    if not _verhoeff_check(raw):
        raise ValueError("Aadhaar checksum is invalid")
    return raw


def validate_ifsc(value: str) -> str:
    ifsc = value.strip().upper()
    if not IFSC_RE.match(ifsc):
        raise ValueError(
            "IFSC must be 11 characters: 4 letters, a 0, then 6 alphanumerics (e.g. HDFC0001234)"
        )
    return ifsc


def validate_uan(value: str) -> str:
    raw = re.sub(r"\s", "", value.strip())
    if not (len(raw) == 12 and raw.isdigit()):
        raise ValueError("UAN must be 12 digits")
    return raw
