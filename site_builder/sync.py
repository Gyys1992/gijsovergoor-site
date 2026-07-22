from __future__ import annotations

import difflib
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

from site_builder.config import SiteConfig
from site_builder.models import (
    Award,
    Presentation,
    PublicProfile,
    PublicSnapshot,
    TeachingRecord,
)
from site_builder.projects import extract_public_projects
from site_builder.tenure import PublicTenureEntry, parse_tenure_log, public_tenure_entries

LOGGER = logging.getLogger(__name__)
ModelT = TypeVar("ModelT", bound=BaseModel)

FORBIDDEN_PUBLIC_TOKENS = (
    "next_action",
    "history",
    "target_journal",
    "candidate_journals",
    "overleaf_project",
    "/Users/",
    "Box-Box",
    "- [ ]",
)


@dataclass(frozen=True)
class SyncResult:
    snapshot: PublicSnapshot
    changed: bool
    diff: str
    path: Path


def load_public_profile(path: Path) -> PublicProfile:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return PublicProfile.model_validate(raw)


def _presentation(entry: PublicTenureEntry) -> Presentation:
    lowered = entry.text.lower()
    kind = (
        "invited_talk"
        if "invited" in lowered or "seminar" in lowered
        else "conference_presentation"
    )
    return Presentation(
        id=entry.id,
        kind=kind,
        year=entry.year,
        date=entry.date,
        title=entry.text,
        venue=entry.text,
        source_key=entry.source_key,
    )


def _award(entry: PublicTenureEntry) -> Award:
    return Award(
        id=entry.id,
        title=entry.text,
        year=entry.year,
        source_key=entry.source_key,
    )


def _course(entry: PublicTenureEntry, institution: str) -> TeachingRecord:
    return TeachingRecord(
        id=entry.id,
        institution=institution,
        course=entry.text,
        level="Recorded in tenure log",
        terms=[entry.date],
        source_key=entry.source_key,
    )


def _merge_by_source_or_id(
    existing: list[ModelT],
    generated: list[ModelT],
) -> list[ModelT]:
    def record_key(record: ModelT) -> str:
        source_key = getattr(record, "source_key", None)
        if source_key:
            return str(source_key)
        if isinstance(record, Presentation):
            normalized_title = re.sub(
                r"[^a-z0-9]+",
                "-",
                record.title.lower(),
            ).strip("-")
            normalized_venue = re.sub(
                r"[^a-z0-9]+",
                "-",
                record.venue.lower(),
            ).strip("-")
            return (
                f"presentation|{record.year}|"
                f"{normalized_title}|{normalized_venue}"
            )
        return str(record.id)

    merged = list(existing)
    keys = {record_key(record) for record in merged}
    for record in generated:
        key = record_key(record)
        if key not in keys:
            merged.append(record)
            keys.add(key)
    return merged


def build_snapshot(config: SiteConfig) -> PublicSnapshot:
    profile = load_public_profile(config.public_profile)
    entries = public_tenure_entries(parse_tenure_log(config.tenure_log))
    presentations = [_presentation(entry) for entry in entries if entry.kind == "talk"]
    awards = [_award(entry) for entry in entries if entry.kind == "award"]
    courses = [
        _course(entry, profile.profile.institution)
        for entry in entries
        if entry.kind == "course"
    ]
    merged_profile = profile.model_copy(
        update={
            "presentations": _merge_by_source_or_id(
                profile.presentations,
                presentations,
            ),
            "awards": _merge_by_source_or_id(profile.awards, awards),
            "teaching": _merge_by_source_or_id(profile.teaching, courses),
        }
    )
    return PublicSnapshot(
        profile=merged_profile,
        projects=extract_public_projects(config.projects_dir),
    )


def serialize_snapshot(snapshot: PublicSnapshot) -> str:
    payload = snapshot.model_dump(mode="json", exclude_none=True)
    return yaml.safe_dump(
        payload,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )


def scan_public_text(text: str, label: str) -> None:
    matches = [token for token in FORBIDDEN_PUBLIC_TOKENS if token in text]
    if matches:
        raise ValueError(f"{label} contains forbidden private tokens: {matches}")


def sync_public(config: SiteConfig) -> SyncResult:
    snapshot = build_snapshot(config)
    new_text = serialize_snapshot(snapshot)
    scan_public_text(new_text, "sanitized snapshot")
    snapshot_path = config.public_data_dir / "snapshot.yaml"
    old_text = (
        snapshot_path.read_text(encoding="utf-8")
        if snapshot_path.exists()
        else ""
    )
    diff = "".join(
        difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile="committed snapshot",
            tofile="current public snapshot",
        )
    )
    changed = old_text != new_text
    if changed:
        config.public_data_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(new_text, encoding="utf-8")
        for line in diff.splitlines():
            LOGGER.info("%s", line)
    else:
        LOGGER.info("Public snapshot is unchanged")
    return SyncResult(
        snapshot=snapshot,
        changed=changed,
        diff=diff,
        path=snapshot_path,
    )
