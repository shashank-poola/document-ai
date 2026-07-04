"""Template-agnostic invoice extraction using multiple competing strategies per field."""

import re
from dataclasses import dataclass

from app.schemas.extraction import InvoiceFields

MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
WRITTEN_DATE_RE = re.compile(
    rf"\b((?:{'|'.join(MONTH_NAMES)})\s+\d{{1,2}},?\s+\d{{4}})\b",
    re.IGNORECASE,
)
NUMERIC_DATE_RE = re.compile(
    r"\b(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2})\b"
)
PLAIN_AMOUNT_RE = re.compile(r"^[\$€£₹]?\s?-?[\d,]+(?:\.\d{2})?$")
CURRENCY_AMOUNT_RE = re.compile(
    r"^(USD|EUR|GBP|INR|CAD|AUD)\s*[\$€£]?\s*(-?[\d,]+\.\d{2})$",
    re.IGNORECASE,
)
CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}

BUYER_LABELS = frozenset(
    {
        "to",
        "to:",
        "bill to",
        "bill to:",
        "ship to",
        "ship to:",
        "invoiced to",
        "invoiced to:",
        "sold to",
        "customer",
    }
)
VENDOR_LABELS = frozenset({"from", "from:", "vendor", "vendor:", "seller", "supplier"})
PARTY_STOP_LABELS = BUYER_LABELS | VENDOR_LABELS | frozenset(
    {
        "invoice number",
        "order number",
        "invoice date",
        "due date",
        "total due",
        "description",
        "transactions",
        "transaction date",
        "amount",
        "balance",
        "credit",
        "sub total",
        "subtotal",
        "total",
        "tax",
        "qty",
        "hrs/qty",
        "service",
        "date:",
    }
)
SUMMARY_LABELS = frozenset({"sub total", "subtotal", "tax", "total", "amount due", "total due"})


@dataclass(frozen=True)
class Candidate:
    value: str
    confidence: float
    source: str


def extract_invoice_fields(text: str) -> InvoiceFields:
    text = _single_document_text(text)
    lines = _normalize_lines(text)

    fields = InvoiceFields(
        invoice_number=_pick(_candidates_invoice_number(text, lines)),
        invoice_date=_pick(_candidates_invoice_date(text, lines)),
        vendor_name=_pick(_candidates_vendor(lines)),
        buyer_name=_pick(_candidates_buyer(lines)),
        currency=_pick(_candidates_currency(text, lines)),
        subtotal=_pick(_candidates_subtotal(text, lines)),
        tax=_pick(_candidates_tax(text, lines)),
        total=_pick(_candidates_total(text, lines)),
        due_date=_pick(_candidates_due_date(text, lines)),
    )

    return fields


def _pick(candidates: list[Candidate]) -> str | None:
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.confidence).value


def _single_document_text(text: str) -> str:
    """When identical invoice pages are merged, extract from the first page only."""
    markers = list(re.finditer(r"^Invoice\s*[#№]", text, re.MULTILINE | re.IGNORECASE))
    if len(markers) >= 2:
        return text[markers[0].start() : markers[1].start()].strip()
    return text


def _normalize_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _normalize_label(line: str) -> str:
    return re.sub(r"[:.\s]+$", "", line.strip().lower())


def _is_date(value: str) -> bool:
    return bool(WRITTEN_DATE_RE.search(value) or NUMERIC_DATE_RE.search(value))


def _is_amount(value: str) -> bool:
    value = value.strip()
    return bool(PLAIN_AMOUNT_RE.match(value) or CURRENCY_AMOUNT_RE.match(value))


def _is_label_line(line: str) -> bool:
    normalized = _normalize_label(line)
    if normalized in PARTY_STOP_LABELS | SUMMARY_LABELS:
        return True
    return normalized.startswith("invoice ") or normalized in {"date", "description", "credit"}


def _candidates_invoice_number(text: str, lines: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []

    patterns = [
        (r"Invoice\s*#\s*([A-Z0-9][A-Z0-9\-/]*)", 0.98, "hash"),
        (r"Invoice\s+(?:No|Number|#)\s*[:\s.]*([A-Z0-9][A-Z0-9\-/]*)", 0.95, "labeled"),
    ]
    for pattern, confidence, source in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidates.append(Candidate(match.group(1), confidence, source))

    for index, line in enumerate(lines):
        if _normalize_label(line) == "invoice number" and index + 1 < len(lines):
            candidates.append(Candidate(lines[index + 1], 0.96, "next_line"))

    return candidates


def _candidates_invoice_date(text: str, lines: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []

    for index, line in enumerate(lines):
        if (
            _normalize_label(line) == "invoice date"
            and index + 1 < len(lines)
            and _is_date(lines[index + 1])
        ):
            candidates.append(Candidate(lines[index + 1], 0.96, "invoice_date_next"))

    match = re.search(
        r"(?<!Transaction\s)(?<!transaction\s)\bDate\b[ \t:]*([^\n]+)",
        text,
        re.IGNORECASE,
    )
    if match and _is_date(match.group(1).strip()):
        candidates.append(Candidate(match.group(1).strip(), 0.92, "date_colon"))

    match = re.search(r"Invoice\s+Date\s*[:\s]+([^\n]+)", text, re.IGNORECASE)
    if match and _is_date(match.group(1).strip()):
        candidates.append(Candidate(match.group(1).strip(), 0.94, "invoice_date_inline"))

    for line in lines:
        if _normalize_label(line).startswith("transaction"):
            continue
        if line.lower().startswith("date:"):
            value = line.split(":", 1)[1].strip()
            if _is_date(value):
                candidates.append(Candidate(value, 0.9, "date_line"))

    return candidates


def _candidates_due_date(text: str, lines: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []

    for index, line in enumerate(lines):
        if (
            _normalize_label(line) == "due date"
            and index + 1 < len(lines)
            and _is_date(lines[index + 1])
        ):
            candidates.append(Candidate(lines[index + 1], 0.96, "due_date_next"))

    match = re.search(r"Due\s+Date\s*[:\s]+([^\n]+)", text, re.IGNORECASE)
    if match and _is_date(match.group(1).strip()):
        candidates.append(Candidate(match.group(1).strip(), 0.94, "due_date_inline"))

    return candidates


def _candidates_vendor(lines: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []

    for index, line in enumerate(lines):
        normalized = _normalize_label(line)
        if normalized in VENDOR_LABELS:
            block = _collect_party_block(lines, index + 1)
            if block:
                candidates.append(Candidate(block[0], 0.94, "from_block"))

        if normalized in BUYER_LABELS:
            for prior in range(index - 1, max(-1, index - 6), -1):
                candidate = lines[prior].strip()
                if candidate and not _is_label_line(candidate) and not _is_amount(candidate):
                    if not candidate.lower().startswith(("phone", "email", "pdf", "powered")):
                        candidates.append(Candidate(candidate, 0.88, "before_buyer"))
                    break

    for pattern, confidence in [
        (r"(?:From|Vendor|Seller|Supplier)\s*[:\s]+([^\n]+)", 0.85),
    ]:
        match = re.search(pattern, "\n".join(lines), re.IGNORECASE)
        if match:
            candidates.append(Candidate(match.group(1).strip(), confidence, "vendor_inline"))

    return candidates


def _candidates_buyer(lines: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []

    for index, line in enumerate(lines):
        normalized = _normalize_label(line)
        if normalized in BUYER_LABELS:
            block = _collect_party_block(lines, index + 1)
            if block:
                candidates.append(Candidate(block[0], 0.94, "buyer_block"))

    for pattern, confidence in [
        (r"(?:Invoiced\s+To|Bill\s+To|Ship\s+To|Sold\s+To|Buyer|Customer)\s*[:\s]+([^\n]+)", 0.86),
    ]:
        match = re.search(pattern, "\n".join(lines), re.IGNORECASE)
        if match:
            candidates.append(Candidate(match.group(1).strip(), confidence, "buyer_inline"))

    return candidates


def _collect_party_block(lines: list[str], start: int) -> list[str]:
    block: list[str] = []
    for line in lines[start:]:
        normalized = _normalize_label(line)
        if normalized in PARTY_STOP_LABELS or normalized.startswith("invoice "):
            break
        if normalized in VENDOR_LABELS | BUYER_LABELS:
            break
        block.append(line)
    return block


def _candidates_currency(text: str, lines: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []

    for line in lines:
        match = CURRENCY_AMOUNT_RE.match(line.strip())
        if match:
            candidates.append(Candidate(match.group(1).upper(), 0.9, "amount_line"))
            break

        if re.search(r"\$\s?[\d,]+\.\d{2}", line):
            candidates.append(Candidate("USD", 0.85, "dollar_sign"))
            break

        code = re.search(r"\b(USD|EUR|GBP|INR|JPY|CAD|AUD)\b", line, re.IGNORECASE)
        if code:
            candidates.append(Candidate(code.group(1).upper(), 0.8, "code"))

    return candidates


def _collect_amount_lines(lines: list[str]) -> list[str]:
    amounts: list[str] = []
    for line in lines:
        stripped = line.strip()
        if CURRENCY_AMOUNT_RE.match(stripped) or PLAIN_AMOUNT_RE.match(stripped):
            amounts.append(stripped)
    return amounts


def _last_amount_after_label(
    lines: list[str],
    labels: set[str],
    *,
    skip_zeros: bool = True,
    require_currency: bool = False,
) -> Candidate | None:
    best: Candidate | None = None
    best_label_index = -1

    for index, line in enumerate(lines):
        if _normalize_label(line) not in labels:
            continue
        for offset in range(1, min(20, len(lines) - index)):
            candidate = lines[index + offset].strip()
            if not _is_amount(candidate):
                continue
            has_currency = "$" in candidate or CURRENCY_AMOUNT_RE.match(candidate)
            if require_currency and not has_currency:
                continue
            if skip_zeros and re.search(r"[\$€£]?\s*0\.00", candidate):
                continue
            if index >= best_label_index:
                best_label_index = index
                confidence = 0.92 - (offset * 0.02)
                best = Candidate(candidate, confidence, f"after_{_normalize_label(line)}")
            break

    return best


def _candidates_subtotal(text: str, lines: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []

    after = _last_amount_after_label(
        lines,
        {"sub total", "subtotal"},
        require_currency=True,
    )
    if after:
        candidates.append(after)

    match = re.search(r"(?m)^\s*Sub\s*Total\s*:\s*([^\n]+)", text, re.IGNORECASE)
    if match:
        value = _normalize_amount_value(match.group(1))
        if _is_amount(value):
            candidates.append(Candidate(value, 0.88, "subtotal_inline"))

    dominant = _dominant_positive_amount(lines)
    if dominant:
        candidates.append(Candidate(dominant, 0.72, "dominant_amount"))

    return candidates


def _candidates_tax(text: str, lines: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []

    after = _last_amount_after_label(lines, {"tax"}, skip_zeros=False, require_currency=True)
    if after:
        candidates.append(after)

    match = re.search(r"(?m)^\s*Tax\s*:\s*([^\n]+)", text, re.IGNORECASE)
    if match:
        value = _normalize_amount_value(match.group(1))
        if _is_amount(value):
            candidates.append(Candidate(value, 0.88, "tax_inline"))

    return candidates


def _candidates_total(text: str, lines: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []

    after = _last_amount_after_label(lines, {"total"}, require_currency=True)
    if after:
        candidates.append(after)

    match = re.search(r"(?m)^\s*Total\s*:\s*([^\n]+)", text, re.IGNORECASE)
    if match:
        value = _normalize_amount_value(match.group(1))
        if _is_amount(value):
            candidates.append(Candidate(value, 0.87, "total_inline"))

    amounts = _collect_amount_lines(lines)
    positive = [amount for amount in amounts if not re.search(r"-[\d,]+\.\d{2}", amount)]
    if positive:
        candidates.append(Candidate(positive[-1], 0.82, "last_positive_amount"))

    dominant = _dominant_positive_amount(lines)
    if dominant:
        candidates.append(Candidate(dominant, 0.85, "dominant_amount"))

    return candidates


def _dominant_positive_amount(lines: list[str]) -> str | None:
    """Pick the most frequent non-zero final amount (handles table/layout reordering)."""
    counts: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if not CURRENCY_AMOUNT_RE.match(stripped):
            continue
        value = float(stripped.split()[-1].replace("$", "").replace(",", ""))
        if value <= 0:
            continue
        counts[stripped] = counts.get(stripped, 0) + 1

    if not counts:
        return None

    return max(counts, key=lambda key: (counts[key], float(key.split()[-1].replace("$", ""))))


def _normalize_amount_value(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"\s+(USD|EUR|GBP|INR|JPY|CAD|AUD)\s*$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _search_date(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    candidate = match.group(1).strip()
    return candidate if _is_date(candidate) else None
