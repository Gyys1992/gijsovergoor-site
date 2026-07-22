from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

APPROVAL_PHRASE = "APPROVE PUBLIC CONTENT"


class ApprovalRequiredError(ValueError):
    """Raised when public content has not been reviewed and approved.

    Covers both failure modes: no approval file yet, and an approval file
    whose recorded digest no longer matches the current snapshot. A
    dedicated subclass lets callers (site_builder.update.main) give
    first-run-friendly guidance instead of an uncaught traceback, while
    existing callers that only expect ValueError keep working unchanged.
    """


def snapshot_digest(snapshot_path: Path) -> str:
    return hashlib.sha256(snapshot_path.read_bytes()).hexdigest()


def approve_snapshot(
    snapshot_path: Path,
    approval_path: Path,
    input_fn: Callable[[str], str] = input,
) -> str:
    response = input_fn(
        f"Review review/public-content-inventory.md, then type "
        f"{APPROVAL_PHRASE}: "
    )
    if response != APPROVAL_PHRASE:
        raise ValueError("public content was not approved")
    digest = snapshot_digest(snapshot_path)
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.write_text(f"{digest}\n", encoding="utf-8")
    return digest


def require_approval(snapshot_path: Path, approval_path: Path) -> None:
    if not approval_path.exists():
        raise ApprovalRequiredError("public content review is required before deployment")
    approved = approval_path.read_text(encoding="utf-8").strip()
    current = snapshot_digest(snapshot_path)
    if approved != current:
        raise ApprovalRequiredError("public snapshot changed; repeat the content review")
