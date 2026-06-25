"""RFC 8785 JSON Canonicalization Scheme (JCS) for CtxGov contracts.

This module implements JCS (RFC 8785) for stable, cross-language digest,
signature, and idempotency inputs. It replaces ``json.dumps(sort_keys=True)``
for long-term contract stability (see ADR-0010).

JCS rules enforced here:
  - UTF-8 output, no insignificant whitespace
  - Object keys sorted by UTF-16 code units (recursively, deepest first)
  - Duplicate keys rejected (not last-wins) so canonicalization is unambiguous
  - NaN / Infinity rejected (not serializable per I-JSON / JCS)
  - Number serialization per ECMA-262 §6.1.6.1.13 (Number::toString):
      * int in [-2^53+1, 2^53-1]: decimal as-is
      * int outside that range: rejected (I-JSON constraint; application must
        represent as string)
      * float: shortest round-trippable representation with ECMAScript
        formatting (lowercase ``e``, explicit ``+``/``-`` exponent sign,
        ``-0`` → ``0``)

The implementation is pure-Python and dependency-free so it can run in
the domain layer without importing any vendor SDK.
"""

from __future__ import annotations

import math
from typing import Any

__all__ = [
    "JCSError",
    "canonicalize",
    "canonicalize_bytes",
    "domain_digest",
]

_INT53_MAX = 2 ** 53 - 1
_INT53_MIN = -(2 ** 53 - 1)


class JCSError(ValueError):
    """Raised when an input cannot be canonicalized under JCS rules."""


def canonicalize(value: Any) -> str:
    """Canonicalize a Python value to a JCS string (RFC 8785)."""
    return _serialize(value).decode("utf-8")


def canonicalize_bytes(value: Any) -> bytes:
    """Canonicalize a Python value to JCS bytes (UTF-8 encoded)."""
    return _serialize(value)


def domain_digest(domain: str, value: Any) -> str:
    """Return a hex sha256 digest over a domain-separated JCS payload.

    ``domain`` is an ASCII label such as ``"ctxgov:state-revision:v2"``.
    The digest input is ``domain + \\x00 + canonical_bytes`` so that two
    identical payloads under different domains cannot be substituted.
    """
    import hashlib

    label = domain.encode("ascii")
    payload = canonicalize_bytes(value)
    seed = label + b"\x00" + payload
    return hashlib.sha256(seed).hexdigest()


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------

def _serialize(value: Any) -> bytes:
    if value is None:
        return b"null"
    if value is True:
        return b"true"
    if value is False:
        return b"false"
    if isinstance(value, int) and not isinstance(value, bool):
        return _serialize_int(value)
    if isinstance(value, float):
        return _serialize_float(value)
    if isinstance(value, str):
        return _serialize_string(value)
    if isinstance(value, (list, tuple)):
        return _serialize_array(value)
    if isinstance(value, dict):
        return _serialize_object(value)
    raise JCSError(f"unsupported JCS value type: {type(value).__name__}")


def _serialize_object(obj: dict[str, Any]) -> bytes:
    seen: set[str] = set()
    parts: list[bytes] = []
    # Sort by UTF-16 code units of the key string (RFC 8785 §3.2.3).
    for key in sorted(obj.keys(), key=_utf16_sort_key):
        if not isinstance(key, str):
            raise JCSError(f"JCS object key must be str, got {type(key).__name__}")
        if key in seen:
            raise JCSError(f"duplicate JCS object key: {key!r}")
        seen.add(key)
        parts.append(_serialize_string(key) + b":" + _serialize(obj[key]))
    return b"{" + b",".join(parts) + b"}"


def _serialize_array(items: Any) -> bytes:
    return b"[" + b",".join(_serialize(item) for item in items) + b"]"


def _serialize_string(text: str) -> bytes:
    out = bytearray(b'"')
    for ch in text:
        code = ord(ch)
        if ch == '"':
            out += b'\\"'
        elif ch == "\\":
            out += b"\\\\"
        elif code < 0x20:
            out += _escape_control(code)
        else:
            out += ch.encode("utf-8")
    out += b'"'
    return bytes(out)


def _escape_control(code: int) -> bytes:
    short = {0x08: b"\\b", 0x09: b"\\t", 0x0A: b"\\n", 0x0C: b"\\f", 0x0D: b"\\r"}
    if code in short:
        return short[code]
    return ("\\u%04x" % code).encode("ascii")


def _utf16_sort_key(text: str) -> tuple[int, ...]:
    """Return a tuple of UTF-16 code unit values for JCS key sorting.

    RFC 8785 §3.2.3 requires sorting property names by their UTF-16 code
    units, not by Unicode code points. For BMP characters (U+0000 to
    U+FFFF) the code unit equals the code point. For supplementary
    characters (U+10000+) the surrogate pair's high surrogate (0xD800-
    0xDBFF) sorts BEFORE any BMP character, which differs from code-point
    order.
    """
    units: list[int] = []
    for ch in text:
        cp = ord(ch)
        if cp <= 0xFFFF:
            units.append(cp)
        else:
            # Encode as UTF-16 surrogate pair.
            cp -= 0x10000
            high = 0xD800 + (cp >> 10)
            low = 0xDC00 + (cp & 0x3FF)
            units.append(high)
            units.append(low)
    return tuple(units)


# ---------------------------------------------------------------------------
# Number serialization
# ---------------------------------------------------------------------------

def _serialize_int(value: int) -> bytes:
    if _INT53_MIN <= value <= _INT53_MAX:
        return str(value).encode("ascii")
    # RFC 8785 builds on I-JSON (RFC 7493 §2.2.1) which says integers
    # outside [-2^53+1, 2^53-1] cannot be represented as JSON numbers
    # without potential loss of precision in other implementations.
    # Reject so the application must explicitly stringify if needed.
    raise JCSError(
        f"integer {value} is outside the JCS/I-JSON safe range "
        f"[-{ _INT53_MAX}, {_INT53_MAX}]; represent as a string "
        f"if the value must be preserved"
    )


def _serialize_float(value: float) -> bytes:
    if math.isnan(value):
        raise JCSError("JCS rejects NaN")
    if math.isinf(value):
        raise JCSError("JCS rejects Infinity")

    # ECMA-262 §6.1.6.1.13: -0 serializes as "0".
    if value == 0.0:
        return b"0"

    sign = b"-" if value < 0 else b""
    value = abs(value)

    # Extract the shortest decimal representation via Python's repr(),
    # then parse into (s, k, n) per ECMA-262 §6.1.6.1.13:
    #   s = significant digits (no leading/trailing zeros)
    #   k = len(s) >= 1
    #   n = position such that value = int(s) * 10^(n - k)
    s, k, n = _decompose_float(value)

    # Apply ECMA-262 Number::toString formatting rules.
    return sign + _format_ecma_float(s, k, n).encode("ascii")


def _decompose_float(value: float) -> tuple[str, int, int]:
    """Decompose ``value`` into (s, k, n) per ECMA-262 §6.1.6.1.13.

    Returns the shortest digit string ``s`` (no leading/trailing zeros),
    its length ``k``, and exponent ``n`` such that
    ``value = int(s) * 10^(n - k)`` and ``10^(k-1) <= int(s) < 10^k``.
    """
    text = repr(value)

    # Parse Python's repr format: "<mantissa>e±<exp>" or "<mantissa>"
    if "e" in text:
        mantissa_text, _, exp_text = text.partition("e")
        e = int(exp_text)
    else:
        mantissa_text = text
        e = 0

    # Split mantissa into integer and fraction parts.
    if "." in mantissa_text:
        int_str, frac_str = mantissa_text.split(".", 1)
    else:
        int_str, frac_str = mantissa_text, ""

    # All raw digits and the position of the implied decimal point.
    raw_digits = int_str + frac_str
    point_pos = len(int_str) + e  # decimal point sits after this many raw digits

    # Strip leading zeros; adjust point_pos.
    stripped = raw_digits.lstrip("0")
    if not stripped:
        return ("0", 1, 0)
    point_pos -= len(raw_digits) - len(stripped)

    # Strip trailing zeros; n stays constant when k decreases.
    stripped_no_trail = stripped.rstrip("0")
    trailing_removed = len(stripped) - len(stripped_no_trail)
    s = stripped_no_trail
    k = len(s)
    # value = int(s) * 10^(n - k) where n = point_pos
    # (point_pos is the number of digits before the decimal in the full
    # expansion; n is defined the same way in ECMA-262.)
    n = point_pos
    return (s, k, n)


def _format_ecma_float(s: str, k: int, n: int) -> str:
    """Format (s, k, n) per ECMA-262 §6.1.6.1.13 Number::toString."""
    if k <= n <= 21:
        # Case 6: all digits before the decimal point, padded with zeros.
        return s + "0" * (n - k)
    if 0 < n <= 21:
        # Case 5: decimal point within the digits.
        return s[:n] + "." + s[n:]
    if -6 < n <= 0:
        # Case 4: 0.00...digits
        return "0." + "0" * (-n) + s
    # Cases 1-3: exponential notation.
    if k == 1:
        mantissa = s
    else:
        mantissa = s[0] + "." + s[1:]
    exp_val = n - 1
    if exp_val >= 0:
        exp_str = "+" + str(exp_val)
    else:
        exp_str = str(exp_val)  # str(neg) already includes "-"
    return f"{mantissa}e{exp_str}"
