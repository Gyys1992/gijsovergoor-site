from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from site_builder.models import Profile, PublicProject, PublicSnapshot, PublicStatus

PORTRAIT_ALT = (
    "Gijs Overgoor, Assistant Professor of Marketing at SMU Cox School of Business"
)


def _profile_values() -> dict[str, object]:
    return yaml.safe_load(
        Path("tests/fixtures/model-profile.yaml").read_text(encoding="utf-8")
    )["profile"]


def test_profile_portrait_alt_defaults_to_none() -> None:
    profile = Profile.model_validate(_profile_values())

    assert profile.portrait_alt is None


def test_profile_accepts_portrait_alt() -> None:
    values = _profile_values()
    values["portrait_alt"] = PORTRAIT_ALT

    profile = Profile.model_validate(values)

    assert profile.portrait_alt == PORTRAIT_ALT


def test_under_review_requires_journal() -> None:
    with pytest.raises(ValidationError, match="journal"):
        PublicProject(
            id="project-example",
            title="An outward-facing title",
            authors=["Gijs Overgoor"],
            status=PublicStatus.UNDER_REVIEW,
            summary="A complete public description.",
            featured=False,
            order=10,
            last_verified="2026-07-17",
        )


def test_preparing_resubmission_requires_journal() -> None:
    with pytest.raises(ValidationError, match="journal"):
        PublicProject(
            id="project-example",
            title="An outward-facing title",
            authors=["Gijs Overgoor"],
            status=PublicStatus.PREPARING_RESUBMISSION,
            summary="A complete public description.",
            featured=False,
            order=10,
            last_verified="2026-07-17",
        )


def test_in_preparation_does_not_publish_target_journal() -> None:
    with pytest.raises(ValidationError, match="must omit journal"):
        PublicProject(
            id="project-example",
            title="An outward-facing title",
            authors=["Gijs Overgoor"],
            status=PublicStatus.IN_PREPARATION,
            journal="Journal of Marketing",
            summary="A complete public description.",
            featured=False,
            order=10,
            last_verified="2026-07-17",
        )


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        PublicProject.model_validate(
            {
                "id": "project-example",
                "title": "An outward-facing title",
                "authors": ["Gijs Overgoor"],
                "status": "research_in_progress",
                "summary": "A complete public description.",
                "featured": False,
                "order": 10,
                "last_verified": "2026-07-17",
                "target_journal": "Private value",
            }
        )


def test_draft_marker_copy_is_rejected() -> None:
    with pytest.raises(ValidationError, match="draft copy"):
        PublicProject(
            id="project-example",
            title="Draft title for replacement",
            authors=["Gijs Overgoor"],
            status=PublicStatus.RESEARCH_IN_PROGRESS,
            summary="A complete public description that is long enough.",
            featured=False,
            order=10,
            last_verified="2026-07-17",
        )


def test_snapshot_rejects_duplicate_ids() -> None:
    profile = yaml.safe_load(
        Path("tests/fixtures/model-profile.yaml").read_text(encoding="utf-8")
    )
    profile["awards"] = [
        {"id": "duplicate-id", "title": "First award"},
        {"id": "duplicate-id", "title": "Second award"},
    ]
    with pytest.raises(ValidationError, match="duplicate public IDs"):
        PublicSnapshot(profile=profile, projects=[])


def test_snapshot_rejects_unknown_work_relationship() -> None:
    profile = yaml.safe_load(
        Path("tests/fixtures/model-profile.yaml").read_text(encoding="utf-8")
    )
    profile["awards"] = [
        {
            "id": "award-example",
            "title": "Example award",
            "related_work_ids": ["missing-work"],
        }
    ]
    with pytest.raises(ValidationError, match="unknown public work IDs"):
        PublicSnapshot(profile=profile, projects=[])
