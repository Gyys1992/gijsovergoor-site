from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from site_builder.approval import ApprovalRequiredError, require_approval
from site_builder.build import BuildResult, build_site
from site_builder.config import SiteConfig, load_config
from site_builder.inventory import write_inventory
from site_builder.sync import SyncResult, sync_public
from site_builder.validate import ValidationReport, validate_site

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class UpdateResult:
    sync: SyncResult
    build: BuildResult
    validation: ValidationReport
    inventory_path: Path


def run_update(config: SiteConfig) -> UpdateResult:
    sync_result = sync_public(config)
    inventory_path = write_inventory(
        sync_result.snapshot,
        config.repository_root / "review/public-content-inventory.md",
    )
    build_result = build_site(config)
    validation = validate_site(config)
    require_approval(
        config.public_data_dir / "snapshot.yaml",
        config.public_data_dir / "APPROVED.sha256",
    )
    return UpdateResult(
        sync=sync_result,
        build=build_result,
        validation=validation,
        inventory_path=inventory_path,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        result = run_update(load_config())
    except ApprovalRequiredError as error:
        LOGGER.error(
            "%s\n"
            "Review review/public-content-inventory.md and the logged snapshot "
            "diff, then run: python -m site_builder.approve\n"
            "Then re-run: python -m site_builder.update",
            error,
        )
        raise SystemExit(1) from None
    LOGGER.info(
        "Updated %d pages; inventory: %s",
        len(result.build.pages),
        result.inventory_path,
    )


if __name__ == "__main__":
    main()
