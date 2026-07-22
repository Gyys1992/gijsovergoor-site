from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

ALLOWED_TAGS = {"talk", "award", "course"}
VENUE_TOKEN = re.compile(r"(?<![A-Za-z0-9_])@([A-Za-z0-9]+(?:-[A-Za-z0-9]+)+)")


@dataclass(frozen=True)
class TenureEntry:
    year: int
    date: str
    tags: frozenset[str]
    text: str


@dataclass(frozen=True)
class PublicTenureEntry:
    id: str
    source_key: str
    year: int
    date: str
    kind: str
    text: str


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _humanize_venue_tokens(value: str) -> str:
    return VENUE_TOKEN.sub(lambda match: match.group(1).replace("-", " "), value)


def parse_tenure_log(path: Path) -> list[TenureEntry]:
    entries: list[TenureEntry] = []
    current_year: int | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        heading = re.fullmatch(r"##\s+(\d{4})\s*", raw_line)
        if heading:
            current_year = int(heading.group(1))
            continue
        if current_year is None or not raw_line.lstrip().startswith("- "):
            continue
        body = raw_line.lstrip()[2:].strip()
        date_match = re.match(r"^(\d{4}(?:-\d{2}(?:-\d{2})?)?)\s+", body)
        date = date_match.group(1) if date_match else str(current_year)
        tags = frozenset(re.findall(r"#([A-Za-z0-9_-]+)", body))
        display = re.sub(r"^\d{4}(?:-\d{2}(?:-\d{2})?)?\s+", "", body)
        display = re.sub(r"#[A-Za-z0-9_-]+\s*", "", display).strip()
        display = _humanize_venue_tokens(display)
        entries.append(
            TenureEntry(
                year=current_year,
                date=date,
                tags=tags,
                text=display,
            )
        )
    return entries


def public_tenure_entries(
    entries: list[TenureEntry],
) -> list[PublicTenureEntry]:
    public: list[PublicTenureEntry] = []
    seen: set[str] = set()
    for entry in entries:
        allowed = entry.tags & ALLOWED_TAGS
        if len(entry.tags) != 1 or len(allowed) != 1:
            continue
        kind = next(iter(allowed))
        source_key = f"{entry.date}|{kind}|{_normalize(entry.text)}"
        if source_key in seen:
            continue
        seen.add(source_key)
        digest = hashlib.sha256(source_key.encode("utf-8")).hexdigest()[:12]
        public.append(
            PublicTenureEntry(
                id=f"tenure-{kind}-{digest}",
                source_key=source_key,
                year=entry.year,
                date=entry.date,
                kind=kind,
                text=entry.text,
            )
        )
    return public
