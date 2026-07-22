from pathlib import Path

import yaml

from site_builder.config import SiteConfig
from site_builder.sync import build_snapshot, serialize_snapshot, sync_public


def make_config(tmp_path: Path) -> SiteConfig:
    vault = tmp_path / "Vault"
    projects = vault / "research/projects"
    projects.mkdir(parents=True)
    (vault / "tenure").mkdir(parents=True)
    (vault / "tenure/public-profile.yaml").write_text(
        Path("tests/fixtures/public-profile.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (vault / "tenure/log.md").write_text(
        Path("tests/fixtures/tenure-log.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (projects / "visible.md").write_text(
        Path("tests/fixtures/projects/visible.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return SiteConfig(
        repository_root=tmp_path,
        canonical_url="https://www.gijsovergoor.com",
        routes=("", "research", "cv", "job-market"),
        vault_root=vault,
        public_profile=vault / "tenure/public-profile.yaml",
        tenure_log=vault / "tenure/log.md",
        projects_dir=projects,
        public_data_dir=tmp_path / "data/public",
        output_dir=tmp_path / "dist",
        templates_dir=tmp_path / "templates",
        static_dir=tmp_path / "static",
        content_dir=tmp_path / "content",
        external_link_timeout_seconds=10.0,
    )


def test_snapshot_contains_only_permitted_sources(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    snapshot = build_snapshot(config)
    text = serialize_snapshot(snapshot)

    assert "Invited Marketing Seminar at Example University" in text
    assert "Example Research Award" in text
    assert "Network Measurement in Digital Platforms" in text
    assert "Private Manuscript" not in text
    assert "Private Submission History" not in text
    assert "Private rejection history" not in text
    assert "target_journal" not in text
    matching_talks = [
        item
        for item in snapshot.profile.presentations
        if item.source_key
        == "2026-07-10|talk|invited-marketing-seminar-at-example-university"
    ]
    assert len(matching_talks) == 1


def test_sync_output_is_deterministic_and_parseable(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    first = sync_public(config)
    second = sync_public(config)
    snapshot_path = config.public_data_dir / "snapshot.yaml"

    assert first.changed is True
    assert second.changed is False
    assert second.diff == ""
    assert yaml.safe_load(snapshot_path.read_text(encoding="utf-8"))["schema_version"] == 1
