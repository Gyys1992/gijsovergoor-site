from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from site_builder.models import PublicProject

PUBLIC_KEYS = {
    "visible",
    "title",
    "authors",
    "status",
    "journal",
    "summary",
    "links",
    "featured",
    "order",
    "last_verified",
}


def _frontmatter(text: str) -> dict[str, Any]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", text, flags=re.DOTALL)
    if match is None:
        return {}
    parsed = yaml.safe_load(match.group(1))
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise ValueError("project frontmatter must be a mapping")
    return parsed


def extract_public_project(path: Path) -> PublicProject | None:
    frontmatter = _frontmatter(path.read_text(encoding="utf-8"))
    candidate = frontmatter.get("public")
    if candidate is None:
        return None
    if not isinstance(candidate, dict):
        raise ValueError(f"{path.name}: public must be a mapping")
    unknown = set(candidate) - PUBLIC_KEYS
    if unknown:
        raise ValueError(f"{path.name}: unsupported public keys: {sorted(unknown)}")
    if candidate.get("visible") is not True:
        return None
    public_data = {key: value for key, value in candidate.items() if key != "visible"}
    public_data["id"] = f"project-{path.stem}"
    return PublicProject.model_validate(public_data)


def extract_public_projects(directory: Path) -> list[PublicProject]:
    records = [
        record
        for path in sorted(directory.glob("*.md"))
        if (record := extract_public_project(path)) is not None
    ]
    return sorted(records, key=lambda record: (record.order, record.title))
