from __future__ import annotations

import logging

from site_builder.approval import approve_snapshot
from site_builder.config import load_config


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_config()
    digest = approve_snapshot(
        config.public_data_dir / "snapshot.yaml",
        config.public_data_dir / "APPROVED.sha256",
    )
    logging.info("Approved public snapshot %s", digest[:12])


if __name__ == "__main__":
    main()
