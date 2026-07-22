from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from site_builder.config import load_config

LOGGER = logging.getLogger(__name__)


def _note_parts(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", text, flags=re.DOTALL)
    if match is None:
        return {}, text
    frontmatter = yaml.safe_load(match.group(1)) or {}
    if not isinstance(frontmatter, dict):
        raise ValueError(f"{path.name}: frontmatter must be a mapping")
    return frontmatter, match.group(2)


def _heading(body: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", body, flags=re.MULTILINE)
    return match.group(1).strip() if match else fallback


def _overview(body: str) -> str:
    match = re.search(
        r"^##\s+Overview\s*$\s*(.+?)(?=^##\s|\Z)",
        body,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        return "No overview paragraph is available; keep this project non-public."
    return " ".join(match.group(1).strip().split())


def _proposed_status(frontmatter: dict[str, Any]) -> str:
    state = " ".join(
        str(frontmatter.get(key, ""))
        for key in ("status", "stage", "pipeline_stage", "focus_status")
    ).lower()
    if "paused" in state or "backburner" in state:
        return "not_public"
    if "r&r" in state or "revise and resubmit" in state:
        return "revise_and_resubmit"
    if "submitted" in state or "under review" in state:
        return "under_review"
    if any(token in state for token in ("analysis", "modeling", "data")):
        return "research_in_progress"
    return "in_preparation"


def render_candidate_report(projects_dir: Path) -> str:
    lines = [
        "# Project Publication Decisions",
        "",
        "Private local review file. No item becomes public until explicitly approved.",
        "",
    ]
    for path in sorted(projects_dir.glob("*.md")):
        frontmatter, body = _note_parts(path)
        status = _proposed_status(frontmatter)
        lines.extend(
            [
                f"## {path.stem}",
                "",
                f"- Proposed title: {_heading(body, path.stem)}",
                f"- Collaborator cue: {frontmatter.get('lead_collaborator', 'confirm from paper')}",
                f"- Proposed status: {status}",
                (
                    f"- Journal cue: {frontmatter.get('target_journal')}"
                    if status in {"revise_and_resubmit", "under_review"}
                    else "- Journal cue: omit from public record"
                ),
                f"- Summary cue: {_overview(body)}",
                "- Public decision: confirm",
                "- Featured decision: confirm",
                "- Verified links: none recorded in the candidate report",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_candidate_report(projects_dir: Path, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_candidate_report(projects_dir), encoding="utf-8")
    return output


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_config()
    output = write_candidate_report(
        config.projects_dir,
        config.repository_root / "review/project-publication-decisions.md",
    )
    LOGGER.info("Wrote private project review to %s", output)


if __name__ == "__main__":
    main()
