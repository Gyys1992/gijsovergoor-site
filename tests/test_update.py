import logging
from pathlib import Path

import pytest

from site_builder import update
from site_builder.approval import ApprovalRequiredError, approve_snapshot
from site_builder.config import SiteConfig
from site_builder.update import run_update
from tests.test_build import prepare_render_files
from tests.test_sync import make_config


def test_update_builds_inventory_and_requires_current_approval(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    prepare_render_files(tmp_path)

    with pytest.raises(ValueError, match="review"):
        run_update(config)

    snapshot_path = config.public_data_dir / "snapshot.yaml"
    approve_snapshot(
        snapshot_path,
        config.public_data_dir / "APPROVED.sha256",
        input_fn=lambda _: "APPROVE PUBLIC CONTENT",
    )
    result = run_update(config)

    assert result.inventory_path.exists()
    assert result.validation.errors == ()


def test_main_logs_guidance_and_exits_nonzero_when_approval_is_required(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def _raise_approval_required(_config: SiteConfig) -> None:
        raise ApprovalRequiredError("public content review is required before deployment")

    monkeypatch.setattr(update, "load_config", lambda: object())
    monkeypatch.setattr(update, "run_update", _raise_approval_required)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as exc_info:
            update.main()

    assert exc_info.value.code == 1
    assert "review/public-content-inventory.md" in caplog.text
    assert "python -m site_builder.approve" in caplog.text
    assert "python -m site_builder.update" in caplog.text
