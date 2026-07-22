from pathlib import Path

import pytest

from site_builder.build import build_site
from site_builder.config import load_config
from site_builder.sync import sync_public
from site_builder.validate import validate_site
from tests.test_build import prepare_render_files
from tests.test_sync import make_config


def test_validation_passes_for_complete_generated_site(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    prepare_render_files(tmp_path)
    sync_public(config)
    build_site(config)

    report = validate_site(config)

    assert report.errors == ()
    # Routes are the four navigable pages from config/site.yaml. /bio is a
    # noindex meta-refresh redirect stub built by build.py's
    # _write_redirect, not a config route, so it is not part of
    # report.routes — but it is still generated here and still scanned by
    # validate_site (see the two redirect-stub tests below), just exempt
    # from the metadata checks that only apply to real templated pages.
    assert set(report.routes) == {"", "research", "cv", "job-market"}


def test_validation_fails_on_private_output_token(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    prepare_render_files(tmp_path)
    sync_public(config)
    build_site(config)
    cv_path = config.output_dir / "cv/index.html"
    cv_path.write_text(
        cv_path.read_text(encoding="utf-8") + "\nnext_action",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="forbidden private"):
        validate_site(config)


def test_validation_fails_on_phone_shaped_number(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    prepare_render_files(tmp_path)
    sync_public(config)
    build_site(config)
    cv_path = config.output_dir / "cv/index.html"
    cv_path.write_text(
        cv_path.read_text(encoding="utf-8") + "\n555 123 4567",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="phone-shaped"):
        validate_site(config)


def test_validation_fails_on_broken_internal_link(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    prepare_render_files(tmp_path)
    sync_public(config)
    build_site(config)
    home = config.output_dir / "index.html"
    home.write_text(
        home.read_text(encoding="utf-8").replace(
            'href="research/"',
            'href="missing/"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="internal link"):
        validate_site(config)


def test_validation_still_flags_forbidden_tokens_in_the_redirect_stub(
    tmp_path: Path,
) -> None:
    # The /bio stub is exempt from metadata checks (see the passing test
    # above) but must not be skipped outright: the privacy scan still has
    # to run on it like any other generated page.
    config = make_config(tmp_path)
    prepare_render_files(tmp_path)
    sync_public(config)
    build_site(config)
    bio_path = config.output_dir / "bio/index.html"
    bio_path.write_text(
        bio_path.read_text(encoding="utf-8") + "\nnext_action",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="forbidden private"):
        validate_site(config)


def test_validation_still_flags_broken_links_in_the_redirect_stub(
    tmp_path: Path,
) -> None:
    # Same idea for internal link/asset resolution: the stub's own link
    # to "../#about" must still be checked.
    config = make_config(tmp_path)
    prepare_render_files(tmp_path)
    sync_public(config)
    build_site(config)
    bio_path = config.output_dir / "bio/index.html"
    bio_path.write_text(
        bio_path.read_text(encoding="utf-8").replace(
            'href="../#about"',
            'href="../missing/#about"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="internal link"):
        validate_site(config)


def test_buzzell_and_media_render_in_both_required_locations() -> None:
    """Regression against the real, committed data/public/snapshot.yaml —
    not the synthetic tests/fixtures profile the tests above use. Confirms
    the production build validates cleanly and that shared relationship
    records render everywhere the current templates place them.

    The invariant: a related award or media record renders once inline
    beneath its related work wherever the current route's template renders
    inline relations, and once more in that route's dedicated Awards /
    Media Coverage section wherever such a dedicated section exists.
    research.html.j2 and cv.html.j2 land on different counts because they
    satisfy that invariant differently, confirmed here by building the real
    snapshot and counting the rendered markers directly (rather than
    assuming a single count for every route):
    - research.html.j2 sets show_related_media=false for its whole render
      and has no dedicated Awards section, so a related award appears once
      (inline, beneath its paper) and related media appears once (only in
      the dedicated Media Coverage section).
    - cv.html.j2 renders inline relations normally and also has dedicated
      Awards and Media Coverage sections, so both awards and media appear
      twice: once inline beneath their paper, once in their dedicated
      section.
    """
    config = load_config()

    build_site(config)
    report = validate_site(config)

    assert report.errors == ()
    for route, expected_count in (("research", 1), ("cv", 2)):
        html = (config.output_dir / route / "index.html").read_text(encoding="utf-8")
        assert (
            html.count('data-award-id="award-buzzell-finalist-2024"') == expected_count
        )
        for media_id in (
            "media-forbes-fake-reviews",
            "media-wsj-fake-reviews",
            "media-business-insider-images",
        ):
            assert html.count(f'data-media-id="{media_id}"') == expected_count
