from __future__ import annotations

from pathlib import Path

import yaml

from site_builder.models import PublicSnapshot


def render_inventory(snapshot: PublicSnapshot) -> str:
    profile = snapshot.profile
    lines = [
        "# Public Content Inventory",
        "",
        "Review every line before approving deployment.",
        "",
        "## Profile",
        "",
        f"- {profile.profile.name}",
        f"- {profile.profile.title}, {profile.profile.institution}",
        f"- {profile.profile.email}",
        f"- {profile.profile.positioning}",
        "",
        "## Publications",
        "",
    ]
    lines.extend(
        f"- [{publication.id}] {publication.citation_html}"
        for publication in profile.publications
        if publication.category == "journal"
    )
    lines.extend(["", "## Conference Proceedings Publications", ""])
    lines.extend(
        f"- [{publication.id}] {publication.citation_html}"
        for publication in profile.publications
        if publication.category == "conference"
    )
    lines.extend(["", "## Working Papers and Research in Progress", ""])
    lines.extend(
        (
            f"- [{project.id}] {project.title} — {project.status.value}"
            + (f" at {project.journal}" if project.journal else "")
        )
        for project in snapshot.projects
    )
    for heading, kind in (
        ("Invited Talks", "invited_talk"),
        ("Conference Presentations", "conference_presentation"),
    ):
        lines.extend(["", f"## {heading}", ""])
        matching = [item for item in profile.presentations if item.kind == kind]
        for year in sorted({item.year for item in matching}, reverse=True):
            lines.append(f"### {year}")
            lines.extend(
                f"- [{item.id}] {item.title}"
                for item in matching
                if item.year == year
            )
    sections = [
        ("Teaching", profile.teaching),
        ("Students and Advising", profile.students),
        ("Media Coverage", profile.media),
        ("Awards", profile.awards),
        ("Academic Service", profile.service),
    ]
    for heading, records in sections:
        lines.extend(["", f"## {heading}", ""])
        for record in records:
            label = (
                getattr(record, "title", None)
                or getattr(record, "course", None)
                or getattr(record, "name", None)
                or getattr(record, "organization", None)
                or getattr(record, "role", None)
                or record.id
            )
            lines.append(f"- [{record.id}] {label}")
    links = list(profile.profile.links)
    for publication in profile.publications:
        links.extend(publication.links)
    for project in snapshot.projects:
        links.extend(project.links)
    lines.extend(["", "## External Links", ""])
    lines.extend(f"- {link.label}: {link.url}" for link in links)
    lines.extend(f"- {mention.outlet}: {mention.url}" for mention in profile.media)
    lines.extend(
        [
            "",
            "## Complete Sanitized Snapshot",
            "",
            "~~~yaml",
            yaml.safe_dump(
                snapshot.model_dump(mode="json", exclude_none=True),
                sort_keys=False,
                allow_unicode=True,
            ).rstrip(),
            "~~~",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_inventory(snapshot: PublicSnapshot, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_inventory(snapshot), encoding="utf-8")
    return path
