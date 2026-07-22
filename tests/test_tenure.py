from pathlib import Path

from site_builder.tenure import TenureEntry, parse_tenure_log, public_tenure_entries


def test_public_filter_emits_only_allowed_tags() -> None:
    fixture = Path("tests/fixtures/tenure-log.md")
    records = public_tenure_entries(parse_tenure_log(fixture))

    assert [record.kind for record in records] == ["talk", "course", "award"]
    rendered = "\n".join(record.text for record in records)
    assert "Private Manuscript" not in rendered
    assert "Private Submission History" not in rendered
    assert "editor praise" not in rendered
    assert "Internal rehearsal" not in rendered


def test_public_ids_are_deterministic() -> None:
    fixture = Path("tests/fixtures/tenure-log.md")
    first = public_tenure_entries(parse_tenure_log(fixture))
    second = public_tenure_entries(parse_tenure_log(fixture))

    assert [record.id for record in first] == [record.id for record in second]
    assert first[0].source_key.startswith("2026-07-10|talk|")


def test_public_filter_rejects_unknown_additional_tag() -> None:
    entry = TenureEntry(
        year=2026,
        date="2026-07-11",
        tags=frozenset({"talk", "confidential"}),
        text="Confidential seminar",
    )

    assert public_tenure_entries([entry]) == []


def test_public_filter_rejects_case_varied_private_tag() -> None:
    entry = TenureEntry(
        year=2026,
        date="2026-07-12",
        tags=frozenset({"talk", "PRIVATE"}),
        text="Private seminar",
    )

    assert public_tenure_entries([entry]) == []


def test_public_text_humanizes_venue_tokens_without_weakening_privacy(
    tmp_path: Path,
) -> None:
    log = tmp_path / "tenure-log.md"
    log.write_text(
        """# Tenure Activity Log

## 2026

- 2026-05-11 #talk @Madison-AI-Symposium presented AdNotator
- 2026-05-10 #talk #private @Madison-AI-Symposium Internal rehearsal
""",
        encoding="utf-8",
    )

    records = public_tenure_entries(parse_tenure_log(log))

    assert [record.text for record in records] == [
        "Madison AI Symposium presented AdNotator"
    ]
