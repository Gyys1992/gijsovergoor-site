from pathlib import Path

import pytest

from site_builder.approval import (
    approve_snapshot,
    require_approval,
    snapshot_digest,
)
from site_builder.inventory import render_inventory
from site_builder.sync import build_snapshot
from tests.test_sync import make_config


def test_inventory_lists_every_public_category(tmp_path: Path) -> None:
    snapshot = build_snapshot(make_config(tmp_path))
    inventory = render_inventory(snapshot)

    assert "# Public Content Inventory" in inventory
    assert "## Profile" in inventory
    assert "## Publications" in inventory
    assert "## Conference Proceedings Publications" in inventory
    assert "## Working Papers and Research in Progress" in inventory
    assert "## Invited Talks" in inventory
    assert "## Conference Presentations" in inventory
    assert "## Media Coverage" in inventory
    assert "## External Links" in inventory
    # Industry Experience and Collaboration was removed as a public category.
    assert "Industry Experience" not in inventory


def test_changed_snapshot_invalidates_approval(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshot.yaml"
    approval_path = tmp_path / "APPROVED.sha256"
    snapshot_path.write_text("schema_version: 1\n", encoding="utf-8")
    approve_snapshot(
        snapshot_path,
        approval_path,
        input_fn=lambda _: "APPROVE PUBLIC CONTENT",
    )
    require_approval(snapshot_path, approval_path)

    snapshot_path.write_text("schema_version: 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="review"):
        require_approval(snapshot_path, approval_path)


def test_digest_is_stable(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshot.yaml"
    snapshot_path.write_text("schema_version: 1\n", encoding="utf-8")
    assert snapshot_digest(snapshot_path) == snapshot_digest(snapshot_path)
