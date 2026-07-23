from pathlib import Path

import yaml
from bs4 import BeautifulSoup

from site_builder.build import build_site
from site_builder.sync import sync_public
from site_builder.validate import PHONE_PATTERN
from tests.test_sync import make_config


def prepare_render_files(config_root: Path) -> None:
    source_root = Path(".")
    for directory in ("templates", "static"):
        destination = config_root / directory
        destination.mkdir(parents=True, exist_ok=True)
        for source in (source_root / directory).rglob("*"):
            if source.is_file():
                target = destination / source.relative_to(source_root / directory)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
    content = config_root / "content"
    content.mkdir()
    (content / "bio.md").write_text("Current biography.", encoding="utf-8")
    (content / "job-market.md").write_text(
        "# Job Market\n\nPreserved essay.",
        encoding="utf-8",
    )


def test_build_emits_exact_routes_and_relative_navigation(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    prepare_render_files(tmp_path)
    sync_public(config)

    result = build_site(config)

    expected = {
        config.output_dir / "index.html",
        config.output_dir / "research/index.html",
        config.output_dir / "cv/index.html",
        config.output_dir / "job-market/index.html",
    }
    assert set(result.pages) == expected
    assert (config.output_dir / "bio/index.html").exists()

    home = BeautifulSoup(
        (config.output_dir / "index.html").read_text(encoding="utf-8"),
        "html.parser",
    )
    research = BeautifulSoup(
        (config.output_dir / "research/index.html").read_text(encoding="utf-8"),
        "html.parser",
    )
    assert home.select_one('a[href="research/"]') is not None
    assert home.select_one('link[href="static/css/site.css"]') is not None
    assert [link.get_text(" ", strip=True) for link in home.select("nav a")] == [
        "Home",
        "Research",
        "CV",
        "Job Market",
    ]
    assert research.select_one('a[href="../cv/"]') is not None
    assert research.select_one('link[href="../static/css/site.css"]') is not None
    assert "bio/" not in (config.output_dir / "sitemap.xml").read_text(
        encoding="utf-8"
    )
    assert "job-market/" in (config.output_dir / "sitemap.xml").read_text(
        encoding="utf-8"
    )


def test_research_intro_names_publication_and_media_venues(
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    prepare_render_files(tmp_path)
    profile = yaml.safe_load(config.public_profile.read_text(encoding="utf-8"))
    profile["publications"].append(
        {
            "id": "proc-fixture-conference",
            "category": "conference",
            "citation_html": "Fixture conference publication.",
            "title": "Fixture Conference Publication",
            "authors": ["Gijs Overgoor"],
            "year": 2026,
            "journal": "Fixture Conference",
            "pages": "1–10",
            "links": [],
        }
    )
    config.public_profile.write_text(
        yaml.safe_dump(profile, sort_keys=False),
        encoding="utf-8",
    )
    sync_public(config)

    build_site(config)

    research = BeautifulSoup(
        (config.output_dir / "research/index.html").read_text(encoding="utf-8"),
        "html.parser",
    )
    intro = research.select_one(".page-intro").get_text(" ", strip=True)
    assert research.select_one("h1").get_text(" ", strip=True) == (
        "My Research"
    )
    assert "Proceedings of the National Academy of Sciences" in intro
    # The "published in" sentence names journal venues only; conference
    # proceedings venues have their own section and must not be listed here.
    assert "Fixture Conference" not in intro
    assert "Forbes" in intro
    assert "Visual marketing, advertising, platforms" not in intro
    assert research.select_one(
        '[data-work-id="proc-fixture-conference"]'
    ) is not None
    assert [
        heading.get_text(" ", strip=True)
        for heading in research.select("main > section > h2")
    ] == [
        "Journal publications",
        "Conference proceedings publications",
        "Current projects",
        "Media coverage",
    ]
    conference_section = research.select("main > section")[1]
    assert conference_section.select_one(
        '[data-work-id="proc-fixture-conference"]'
    ) is not None


def test_related_media_and_awards_use_shared_records(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    prepare_render_files(tmp_path)
    sync_public(config)

    build_site(config)

    research = (config.output_dir / "research/index.html").read_text(
        encoding="utf-8"
    )
    cv = (config.output_dir / "cv/index.html").read_text(encoding="utf-8")
    assert research.count('data-award-id="award-buzzell-finalist-2024"') == 1
    assert cv.count('data-award-id="award-buzzell-finalist-2024"') == 2
    assert research.count('data-media-id="media-forbes-fake-reviews"') == 1
    assert cv.count('data-media-id="media-forbes-fake-reviews"') == 2


def test_home_uses_the_snapshot_portrait_alt_text(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    prepare_render_files(tmp_path)
    profile = yaml.safe_load(config.public_profile.read_text(encoding="utf-8"))
    profile["profile"]["portrait_alt"] = "Fixture-specific portrait description"
    config.public_profile.write_text(
        yaml.safe_dump(profile, sort_keys=False),
        encoding="utf-8",
    )
    sync_public(config)

    build_site(config)

    home = BeautifulSoup(
        (config.output_dir / "index.html").read_text(encoding="utf-8"),
        "html.parser",
    )
    portrait = home.select_one(".hero img")
    assert portrait is not None
    assert portrait.get("alt") == "Fixture-specific portrait description"


def test_home_includes_profile_and_bio_copy_without_project_duplication(
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    prepare_render_files(tmp_path)
    profile = yaml.safe_load(config.public_profile.read_text(encoding="utf-8"))
    profile["profile"]["institution"] = "SMU Cox School of Business"
    profile["profile"]["short_positioning"] = (
        "I study advertising and digital platforms, with a particular focus on "
        "visual content. My work combines AI, econometrics, surveys and "
        "experiments, and neuroscience."
    )
    profile["profile"]["positioning"] = (
        "I develop and validate AI-based measures for unstructured marketing data."
    )
    config.public_profile.write_text(
        yaml.safe_dump(profile, sort_keys=False),
        encoding="utf-8",
    )
    sync_public(config)

    build_site(config)

    home = BeautifulSoup(
        (config.output_dir / "index.html").read_text(encoding="utf-8"),
        "html.parser",
    )
    assert home.select_one(".hero .eyebrow").get_text(" ", strip=True) == (
        "Assistant Professor of Marketing · SMU Cox School of Business"
    )
    assert home.select_one(".lede").get_text(" ", strip=True).startswith(
        "I study advertising and digital platforms"
    )
    assert home.select_one("#about h2").get_text(" ", strip=True) == "About Me"
    paragraphs = home.select("#about .prose > p")
    assert paragraphs[0].get_text(" ", strip=True).startswith(
        "I develop and validate AI-based measures"
    )
    assert paragraphs[1].get_text(" ", strip=True) == "Current biography."
    assert "Selected projects" not in home.get_text(" ", strip=True)


def test_preparing_resubmission_uses_exact_public_status_text(
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    prepare_render_files(tmp_path)
    (config.projects_dir / "resubmission.md").write_text(
        """---
public:
  visible: true
  title: "Resubmission Project"
  authors:
    - "Gijs Overgoor"
  status: "preparing_resubmission"
  journal: "Journal of Marketing Research"
  summary: "A complete public description of the resubmission project."
  links: []
  featured: true
  order: 5
  last_verified: "2026-07-18"
---
""",
        encoding="utf-8",
    )
    sync_public(config)

    build_site(config)

    for route in ("research/index.html", "cv/index.html"):
        page = (config.output_dir / route).read_text(encoding="utf-8")
        assert (
            "In preparation for resubmission to Journal of Marketing Research"
            in page
        )


def test_cv_is_continuous_and_omits_prohibited_content(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    prepare_render_files(tmp_path)
    profile = yaml.safe_load(config.public_profile.read_text(encoding="utf-8"))
    profile["presentations"].append(
        {
            "id": "presentation-fixture-conference",
            "kind": "conference_presentation",
            "year": 2025,
            "title": "Fixture Conference Presentation",
            "venue": "Fixture Conference",
        }
    )
    profile["presentations"].append(
        {
            "id": "talk-fixture-amazon",
            "kind": "invited_talk",
            "year": 2026,
            "title": "Invited Marketing Seminar at Amazon (presented research)",
            "venue": "Amazon",
        }
    )
    config.public_profile.write_text(
        yaml.safe_dump(profile, sort_keys=False),
        encoding="utf-8",
    )
    (config.projects_dir / "work-in-progress.md").write_text(
        """---
public:
  visible: true
  title: "Public Work in Progress"
  authors:
    - "Gijs Overgoor"
  status: "research_in_progress"
  summary: "A complete public description of ongoing fixture research."
  links: []
  featured: false
  order: 20
  last_verified: "2026-07-17"
---
""",
        encoding="utf-8",
    )
    sync_public(config)

    build_site(config)

    cv = BeautifulSoup(
        (config.output_dir / "cv/index.html").read_text(encoding="utf-8"),
        "html.parser",
    )
    headings = [heading.get_text(" ", strip=True) for heading in cv.select(".cv > section > h2")]
    assert headings == [
        "Academic Positions",
        "Education",
        "Research Interests",
        "Published Papers",
        "Working Papers",
        "Selected Work in Progress",
        "Peer-Reviewed Conference Proceedings",
        "Invited Talks",
        "Conference Presentations",
        "Teaching",
        "Students and Advising",
        "Consulting and Expert Witness Work",
        "Media Coverage",
        "Awards",
        "Academic Service",
        "Technical Strengths and Languages",
    ]
    cv_text = cv.get_text(" ", strip=True)
    assert PHONE_PATTERN.search(cv_text) is None
    assert "References" not in cv_text
    assert "Download CV" not in cv_text
    assert "I undertake consulting and expert witness work." in cv_text
    # Structural invariant, not company-name literals: the fixture profile's
    # industry list is empty and cv.html.j2 has no Industry section at all,
    # so no Industry Experience entries can ever render here regardless of
    # what any real profile.industry might contain.
    assert "Industry Experience and Collaboration" not in cv_text
    assert "Invited Marketing Seminar at" not in cv_text
    assert "Amazon (presented research)" not in cv_text
    assert "Amazon" in cv_text
    assert cv.select_one('a[href="mailto:govergoor@smu.edu"]') is not None
    assert cv.select_one(
        'a[href="https://www.linkedin.com/in/gijs-overgoor-phd-4145a464/"]'
    ) is not None
    assert cv.select_one("a[download]") is None
