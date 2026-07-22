from pathlib import Path

from site_builder.candidates import write_candidate_report


def test_candidate_report_stays_in_ignored_review_directory(
    tmp_path: Path,
) -> None:
    projects = tmp_path / "Vault/research/projects"
    projects.mkdir(parents=True)
    (projects / "example.md").write_text(
        """---
target_journal: JMR
stage: Revise and resubmit at JMR
status: R&R
lead_collaborator: Example Coauthor
---
# Example Visual Marketing Paper

## Overview

Examines visual advertising outcomes using multiple methods.
""",
        encoding="utf-8",
    )
    output = tmp_path / "review/project-publication-decisions.md"

    write_candidate_report(projects, output)

    report = output.read_text(encoding="utf-8")
    assert "Example Visual Marketing Paper" in report
    assert "revise_and_resubmit" in report
    assert "Example Coauthor" in report
    assert not (tmp_path / "data/public").exists()
