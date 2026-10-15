"""Record tables: marksheet subjects, bank transactions and ration-card members.

Two sources are handled:

* table spans from the PDF parser (cells separated by `` | ``, one row per line);
* OCR or plain-text rows under a recognised header line, used only when the page
  has no table span of that kind.

Values are kept as printed (descriptions, codes and references with leading
zeros); numbers are normalised ('082' -> '82', '5,000.00' -> '5000.00').
Nothing is guessed: a transaction's debit/credit direction is taken from its
column, or, for column-less OCR rows, from the change in running balance; when
neither is available the amount is stored without a direction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.extraction.normalize import normalize_amount, normalize_date, normalize_number
from app.processing.schemas import NormalizedPage

# (column key, pattern) - first match wins, so specific headers come first.
_MARK_COLUMNS = (
    ("total_in_words", re.compile(r"in\s*words", re.I)),
    (
        "practical_or_internal",
        re.compile(
            r"\b(ia\s*/\s*pr|pr\s*/\s*ia|prac\.?\s*/\s*ia|ia\s*/\s*prac|internal\s*/\s*practical|practical\s*/\s*internal)\b",
            re.I,
        ),
    ),
    ("grade", re.compile(r"grade", re.I)),
    ("marks_obtained", re.compile(r"obtain|secured", re.I)),
    ("max_marks", re.compile(r"\bmax", re.I)),
    ("code", re.compile(r"code", re.I)),
    ("theory", re.compile(r"\btheory\b|\bth\b", re.I)),
    ("practical", re.compile(r"\bpractical\b|\bpr\b", re.I)),
    ("internal", re.compile(r"\binternal\b|\bia\b|\bint\b", re.I)),
    ("total", re.compile(r"\btotal\b", re.I)),
    ("result", re.compile(r"result|status", re.I)),
    ("name", re.compile(r"subject|paper|course|\bsub\b", re.I)),
)
_MARKS_HEADER_HINT = re.compile(r"subject|paper|\bsub\b", re.I)
_TXN_COLUMNS = (
    ("date", re.compile(r"date", re.I)),
    ("description", re.compile(r"particular|description|narration|details|remarks", re.I)),
    ("reference", re.compile(r"ref|cheque|chq|instrument", re.I)),
    ("debit", re.compile(r"debit|withdraw|\bdr\b", re.I)),
    ("credit", re.compile(r"credit|deposit|\bcr\b", re.I)),
    ("balance", re.compile(r"balance", re.I)),
)
_MEMBER_COLUMNS = (
    ("serial", re.compile(r"^\s*(sr|s\.?\s*no|serial)", re.I)),
    ("relation", re.compile(r"relation", re.I)),
    ("age", re.compile(r"\bage\b", re.I)),
    ("gender", re.compile(r"gender|sex", re.I)),
    ("name", re.compile(r"name", re.I)),
)
_NUMERIC_MARK_KEYS = {
    "theory",
    "practical",
    "internal",
    "practical_or_internal",
    "total",
    "max_marks",
    "marks_obtained",
}
_GRADE = re.compile(r"^(?:[A-E][1-2]?|[A-D]\+{0,2}|O|P|F|AB)$")
_NUMBER_WORDS = set(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty "
    "ninety hundred only".split()
)
_TOTAL_ROW = re.compile(r"^\s*(grand\s+)?total\b", re.I)
_DATE_START = re.compile(r"^(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\s+(.*)$")
_AMOUNT = re.compile(r"^-?\d[\d,]*\.\d{2}$")


@dataclass
class TableRecord:
    kind: str  # subject | transaction | member
    values: dict[str, str]
    page: int
    evidence: str
    method: str = "table"


@dataclass
class MarksTotals:
    values: dict[str, str] = field(default_factory=dict)
    page: int | None = None
    evidence: str = ""


@dataclass
class TableResult:
    records: list[TableRecord] = field(default_factory=list)
    totals: MarksTotals = field(default_factory=MarksTotals)


def _map_header(
    cells: list[str], columns: tuple[tuple[str, re.Pattern[str]], ...]
) -> list[str | None]:
    mapped: list[str | None] = []
    used: set[str] = set()
    for cell in cells:
        key = next((k for k, pattern in columns if pattern.search(cell) and k not in used), None)
        if key:
            used.add(key)
        mapped.append(key)
    return mapped


def _cells(row: str) -> list[str]:
    return (
        [cell.strip() for cell in re.split(r"\s*\|\s*", row.strip())]
        if "|" in row
        else [row.strip()]
    )


_OCR_DIGIT_LOOKALIKES = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1"})


def repair_numeric(text: str) -> str:
    """'10O' -> '100' in a numeric column: OCR look-alikes, only when the cell is
    otherwise all digits (a grade such as 'O' or 'A1' is left alone)."""
    if len(text) >= 2 and re.fullmatch(r"[0-9OolI|.,]+", text) and any(ch.isdigit() for ch in text):
        return text.translate(_OCR_DIGIT_LOOKALIKES)
    return text


def _mark_value(key: str, raw: str, record: dict[str, str]) -> None:
    text = raw.strip()
    if not text or text in ("--", "-", "—"):
        return
    if key in _NUMERIC_MARK_KEYS:
        text = repair_numeric(text)
        number = normalize_number(text)
        if number is not None:
            record[key] = number
        elif _GRADE.match(text.upper()):
            # a grade printed in a marks column (grade-only subjects)
            record["grade" if text.upper() != "AB" else "status"] = (
                text.upper() if text.upper() != "AB" else "ABSENT"
            )
        return
    record[key] = text


# ---------------------------------------------------------------------- marks


def _table_texts(page: NormalizedPage) -> list[str]:
    """Table texts of a page: parser/OCR table spans, else runs of ``|``-separated lines.

    Text exports and some scans print tables as "Code | Subject | Marks" lines
    without a table span; two or more consecutive such lines are read as a table.
    """
    texts = [span.text for span in page.spans if span.is_table]
    if texts:
        return texts
    blocks: list[str] = []
    current: list[str] = []
    for span in page.spans:
        for line in span.text.splitlines():
            if line.count("|") >= 2:
                current.append(line)
                continue
            if len(current) >= 2:
                blocks.append("\n".join(current))
            current = []
    if len(current) >= 2:
        blocks.append("\n".join(current))
    return blocks


def parse_marks(pages: list[NormalizedPage]) -> TableResult:
    result = TableResult()
    for page in pages:
        found = False
        for text in _table_texts(page):
            rows = [r for r in text.split("\n") if r.strip(" |")]
            header_index = next(
                (
                    i
                    for i, r in enumerate(rows)
                    if sum(k is not None for k in _map_header(_cells(r), _MARK_COLUMNS)) >= 2
                    and _MARKS_HEADER_HINT.search(r)
                ),
                None,
            )
            if header_index is None:
                continue
            found = True
            header = _map_header(_cells(rows[header_index]), _MARK_COLUMNS)
            for row in rows[header_index + 1 :]:
                cells = _cells(row)
                record: dict[str, str] = {}
                for key, cell in zip(header, cells, strict=False):
                    if key:
                        _mark_value(key, cell, record)
                if _TOTAL_ROW.match(cells[0]) or _TOTAL_ROW.match(record.get("name", "")):
                    _set_totals(result, record, page.page_number, row)
                    continue
                if record.get("name") and re.search(r"[A-Za-z]", record["name"]):
                    record.pop("total_in_words", None)
                    result.records.append(TableRecord("subject", record, page.page_number, row))
        if not found:
            _parse_mark_lines(page, result)
    return result


def _set_totals(result: TableResult, record: dict[str, str], page: int, evidence: str) -> None:
    totals = {}
    if record.get("max_marks"):
        totals["max_marks"] = record["max_marks"]
    obtained = record.get("marks_obtained") or record.get("total")
    if obtained:
        totals["marks_obtained"] = obtained
    if totals:
        result.totals = MarksTotals(totals, page, evidence)


def _parse_mark_lines(page: NormalizedPage, result: TableResult) -> None:
    lines = [
        line.strip() for span in page.spans if not span.is_table for line in span.text.splitlines()
    ]
    header_at = None
    for index, line in enumerate(lines):
        if re.search(r"subject", line, re.I) and re.search(
            r"marks|obtain|grade|theory|total", line, re.I
        ):
            header_at = index
            break
    if header_at is None:
        return
    header = lines[header_at].lower()
    positions = []
    for key, pattern in (
        ("max_marks", r"\bmax"),
        ("theory", r"\btheory\b"),
        ("practical_or_internal", r"\bia\s*/\s*pr\b|\bpr\s*/\s*ia\b"),
        ("marks_obtained", r"obtain|secured"),
    ):
        match = re.search(pattern, header)
        if match:
            positions.append((match.start(), key))
    total_match = re.search(r"\btotal\b(?!\s*\(?in words)", header)
    if total_match and "marks_obtained" not in {k for _, k in positions}:
        positions.append((total_match.start(), "total"))
    numeric_columns = [key for _, key in sorted(positions)]
    has_code = "code" in header
    has_grade = "grade" in header
    has_words = "words" in header
    misses = 0
    for line in lines[header_at + 1 :]:
        if _TOTAL_ROW.match(line):
            numbers = [normalize_number(t) for t in line.split()[1:]]
            numbers = [n for n in numbers if n is not None]
            record = dict(zip(numeric_columns, numbers, strict=False))
            _set_totals(result, record, page.page_number, line)
            break
        record = _parse_mark_line(line, numeric_columns, has_code, has_grade, has_words)
        if record is None:
            misses += 1
            if misses >= 2:
                break
            continue
        misses = 0
        result.records.append(TableRecord("subject", record, page.page_number, line, "table_text"))


def _parse_mark_line(
    line: str, numeric_columns: list[str], has_code: bool, has_grade: bool, has_words: bool
) -> dict[str, str] | None:
    tokens = line.split()
    if len(tokens) < 2 or not numeric_columns:
        return None
    record: dict[str, str] = {}
    if has_code and re.fullmatch(r"[A-Z]?\d{2,4}", tokens[0]):
        record["code"] = tokens.pop(0)
    if has_grade and tokens and _GRADE.match(tokens[-1].upper()):
        record["grade"] = tokens.pop().upper()
    if has_words:
        while tokens and tokens[-1].lower() in _NUMBER_WORDS:
            tokens.pop()
    trailing: list[str] = []
    while tokens and (
        re.fullmatch(r"\d{1,3}|--|-", tokens[-1])
        or (_GRADE.match(tokens[-1].upper()) and len(tokens[-1]) <= 2)
    ):
        trailing.insert(0, tokens.pop())
    name = " ".join(tokens)
    if not trailing or not re.search(r"[A-Za-z]{2,}", name):
        return None
    record["name"] = name
    for key, raw in zip(numeric_columns, trailing, strict=False):
        _mark_value(key, raw, record)
    return record


# ---------------------------------------------------------------------- transactions


def parse_transactions(pages: list[NormalizedPage]) -> list[TableRecord]:
    records: list[TableRecord] = []
    for page in pages:
        found = False
        for text in _table_texts(page):
            rows = [r for r in text.split("\n") if r.strip(" |")]
            header_index = next(
                (
                    i
                    for i, r in enumerate(rows)
                    if {"date", "balance"}
                    <= set(filter(None, _map_header(_cells(r), _TXN_COLUMNS)))
                ),
                None,
            )
            if header_index is None:
                continue
            header = _map_header(_cells(rows[header_index]), _TXN_COLUMNS)
            found = True
            for row in rows[header_index + 1 :]:
                record: dict[str, str] = {}
                for key, cell in zip(header, _cells(row), strict=False):
                    if not key or not cell.strip():
                        continue
                    if key == "date":
                        iso = normalize_date(cell)
                        if iso:
                            record["date"] = iso
                    elif key in ("debit", "credit", "balance"):
                        amount = normalize_amount(cell)
                        if amount is not None:
                            record[key] = amount
                    else:
                        record[key] = cell.strip()
                if record.get("date"):
                    records.append(TableRecord("transaction", record, page.page_number, row))
        if not found:
            records.extend(_parse_transaction_lines(page))
    return records


def _parse_transaction_lines(page: NormalizedPage) -> list[TableRecord]:
    lines = [
        line.strip() for span in page.spans if not span.is_table for line in span.text.splitlines()
    ]
    header_at = next(
        (
            i
            for i, line in enumerate(lines)
            if re.search(r"\bdate\b", line, re.I)
            and re.search(r"balance", line, re.I)
            and re.search(r"debit|credit|withdraw|deposit|amount", line, re.I)
        ),
        None,
    )
    if header_at is None:
        return []
    records: list[TableRecord] = []
    previous_balance: float | None = None
    for line in lines[header_at + 1 :]:
        match = _DATE_START.match(line)
        if not match:
            continue
        iso = normalize_date(match.group(1))
        tokens = match.group(2).split()
        amounts: list[str] = []
        while tokens and _AMOUNT.match(tokens[-1]):
            amounts.insert(0, tokens.pop())
        if not iso or not amounts or len(amounts) > 2:
            continue
        record = {"date": iso, "description": " ".join(tokens)}
        balance = normalize_amount(amounts[-1])
        record["balance"] = balance or ""
        if len(amounts) == 2:
            amount = normalize_amount(amounts[0]) or ""
            if previous_balance is not None and balance is not None:
                delta = float(balance) - previous_balance
                if abs(abs(delta) - float(amount)) < 0.005:
                    record["debit" if delta < 0 else "credit"] = amount
                else:
                    record["amount"] = amount
            else:
                record["amount"] = amount
        previous_balance = float(balance) if balance is not None else None
        records.append(
            TableRecord(
                "transaction",
                {k: v for k, v in record.items() if v},
                page.page_number,
                line,
                "table_text",
            )
        )
    return records


# ---------------------------------------------------------------------- members


def parse_members(pages: list[NormalizedPage]) -> list[TableRecord]:
    records: list[TableRecord] = []
    for page in pages:
        for text in _table_texts(page):
            rows = [r for r in text.split("\n") if r.strip(" |")]
            if not rows:
                continue
            header = _map_header(_cells(rows[0]), _MEMBER_COLUMNS)
            if not {"name", "relation"} <= set(filter(None, header)):
                continue
            for row in rows[1:]:
                record: dict[str, Any] = {
                    key: cell.strip()
                    for key, cell in zip(header, _cells(row), strict=False)
                    if key and key != "serial" and cell.strip()
                }
                if record.get("name"):
                    records.append(TableRecord("member", record, page.page_number, row))
    return records
