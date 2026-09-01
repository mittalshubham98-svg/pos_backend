"""Small stateless helpers shared across routers/services: ID/password generation,
Indian-style rupee formatting, and amount-in-words for the invoice."""
import re
import secrets
import string
from typing import Iterable, Optional, Set


def gen_cust_code(name: Optional[str], existing: Optional[Set[str]] = None) -> str:
    """A short, memorable ID derived from the customer's name, e.g. "Ramesh Kumar" ->
    RAMESH01. Letters only, uppercased, capped at 6 characters, plus a 2+ digit counter to
    keep it unique (widening to 3, then 4 digits if the short forms of two names collide).
    Falls back to "CUST" when the name has no usable letters (e.g. blank/numeric)."""
    existing = existing or set()
    letters = re.sub(r"[^A-Za-z]", "", name or "").upper()
    base = letters[:6] or "CUST"
    for digits in (2, 3, 4):
        for n in range(1, 10 ** digits):
            code = f"{base}{n:0{digits}d}"
            if code not in existing:
                return code
    # Astronomically unlikely fallback if every 4-digit suffix for this base is taken.
    return f"{base}{secrets.token_hex(3).upper()}"


def gen_password(length: int = 8) -> str:
    """Random uppercase alphanumeric password, handed to the admin once in plaintext."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def gen_otp(length: int = 6) -> str:
    """Random numeric OTP for the mobile-number self-service password reset flow."""
    return "".join(secrets.choice(string.digits) for _ in range(length))


def gen_po_number(next_seq: int) -> str:
    return f"PO-{next_seq}"


def clean_utr(raw: Optional[str]) -> str:
    """Strip everything but digits. A blank result means 'on account' (no UTR)."""
    if not raw:
        return ""
    return re.sub(r"\D", "", raw)


def _indian_grouping(num_str: str) -> str:
    """1234567 -> '12,34,567' (last 3 digits, then groups of 2)."""
    if "." in num_str:
        whole, frac = num_str.split(".", 1)
    else:
        whole, frac = num_str, None
    neg = whole.startswith("-")
    if neg:
        whole = whole[1:]
    if len(whole) > 3:
        last3 = whole[-3:]
        rest = whole[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        whole = ",".join(groups + [last3])
    result = ("-" if neg else "") + whole
    if frac is not None:
        result += "." + frac
    return result


def inr(n: float) -> str:
    """₹ with 2 decimals and Indian digit grouping, e.g. inr(17575.4) -> '₹17,575.40'."""
    n = round(float(n or 0), 2)
    return "₹" + _indian_grouping(f"{n:.2f}")


def inr0(n: float) -> str:
    """₹ rounded to the nearest whole rupee, e.g. inr0(17575.4) -> '₹17,575'."""
    n = int(round(float(n or 0)))
    return "₹" + _indian_grouping(str(n))


_ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
    "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
    "Eighteen", "Nineteen",
]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two_digits(n: int) -> str:
    if n < 20:
        return _ONES[n]
    tail = _ONES[n % 10]
    return (_TENS[n // 10] + (" " + tail if tail else "")).strip()


def _three_digits(n: int) -> str:
    if n >= 100:
        rest = _two_digits(n % 100)
        return _ONES[n // 100] + " Hundred" + (" " + rest if rest else "")
    return _two_digits(n)


def amount_in_words_inr(amount: float) -> str:
    """Rupee amount -> words, Indian numbering system (crore/lakh/thousand).

    amount_in_words_inr(17575) == 'Seventeen Thousand Five Hundred Seventy Five Rupees Only'
    — matches the reference invoice's 'Amount in words' line exactly.
    """
    n = int(round(abs(float(amount))))
    if n == 0:
        return "Zero Rupees Only"

    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, hundred = divmod(n, 1_000)

    parts = []
    if crore:
        parts.append(_three_digits(crore) + " Crore")
    if lakh:
        parts.append(_three_digits(lakh) + " Lakh")
    if thousand:
        parts.append(_three_digits(thousand) + " Thousand")
    if hundred:
        parts.append(_three_digits(hundred))

    return " ".join(parts) + " Rupees Only"


def dedupe_preserve_order(items: Iterable[str]) -> list:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
