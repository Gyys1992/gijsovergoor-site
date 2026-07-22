import json
from pathlib import Path

from site_builder.projects import extract_public_project, extract_public_projects


def test_extractor_uses_only_public_block() -> None:
    record = extract_public_project(Path("tests/fixtures/projects/visible.md"))

    assert record is not None
    assert record.id == "project-visible"
    serialized = json.dumps(record.model_dump(mode="json"))
    assert "Private Journal" not in serialized
    assert "Private rejection history" not in serialized
    assert "Private task" not in serialized
    assert "Reviewer comments" not in serialized


def test_hidden_and_missing_public_blocks_are_excluded() -> None:
    records = extract_public_projects(Path("tests/fixtures/projects"))

    assert [record.id for record in records] == ["project-visible"]
