"""Content-contract tests against the real, committed public snapshot.

Adding or removing a public project intentionally requires updating the
expected inventory in test_required_public_content_contract below.
"""

import hashlib
import re
from pathlib import Path

import yaml

from site_builder.config import load_config
from site_builder.models import PublicSnapshot
from site_builder.validate import PHONE_PATTERN


def _normalized_body_text(text: str) -> str:
    normalized_lines = [
        line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]
    return "\n".join(normalized_lines).strip() + "\n"


def test_required_public_content_contract() -> None:
    config = load_config()
    snapshot_path = config.public_data_dir / "snapshot.yaml"
    snapshot = PublicSnapshot.model_validate(
        yaml.safe_load(snapshot_path.read_text(encoding="utf-8"))
    )
    profile = snapshot.profile
    publication_ids = {publication.id for publication in profile.publications}
    pnas = next(
        publication
        for publication in profile.publications
        if publication.id == "pub-he-2022-fake-review-buyers"
    )
    buzzell = next(
        award
        for award in profile.awards
        if award.id == "award-buzzell-finalist-2024"
    )
    adsum = next(
        publication
        for publication in profile.publications
        if publication.id == "proc-xie-2026-adsum"
    )
    all_text = snapshot_path.read_text(encoding="utf-8")
    projects = {project.id: project for project in snapshot.projects}
    expected_projects = {
        "project-basoa-impact-combined": {
            "title": (
                "How Consistency and Timing Shape Consumer Responses to Racial "
                "Representation in TV Advertising"
            ),
            "authors": [
                "Gijs Overgoor",
                "Lijing Wang",
                "Gokhan Yildirim",
                "Yakov Bart",
                "Koen Pauwels",
            ],
            "status": "revise_and_resubmit",
            "journal": "Journal of Marketing Research",
            "featured": True,
            "order": 10,
            "links": [
                ("SSRN", "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4471248"),
            ],
        },
        "project-champions-neurovit": {
            "title": "NeuroViT: A Brain-Aligned Vision Transformer for Product Image Analysis",
            "authors": [
                "Gijs Overgoor",
                "Hang-Yee Chan",
                "William Rand",
                "Willemijn van Dolen",
            ],
            "status": "under_review",
            "journal": "Journal of Marketing Research",
            "featured": True,
            "order": 20,
            "links": [
                ("SMU Scholar", "https://scholar.smu.edu/business_marketing_research/61/"),
                ("SSRN", "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5272560"),
            ],
        },
        "project-adnotator-video-understanding": {
            "title": (
                "Correcting Toward the Wrong Target: LLM-Annotated Regressors "
                "Under Noisy Human Benchmarks"
            ),
            "authors": ["Gijs Overgoor", "Samsun Knight", "Yakov Bart"],
            "status": "in_preparation",
            "journal": None,
            "featured": True,
            "order": 30,
            "links": [
                ("SMU Scholar", "https://scholar.smu.edu/business_marketing_research/59/"),
                ("SSRN", "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5494548"),
            ],
        },
        "project-fake-review": {
            "title": "Public traces expose coordinated fake review campaigns on digital platforms",
            "authors": [
                "Gijs Overgoor",
                "Ali Tosyali",
                "Ethan Feldman",
                "Anol Bhattacherjee",
            ],
            "status": "in_preparation",
            "journal": None,
            "featured": True,
            "order": 40,
            "links": [
                ("SSRN", "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5156231"),
            ],
        },
        "project-tv-ads-impact-dollar-value": {
            "title": (
                "The Dollar Value of Better Ad Content: Tracing the Relationships "
                "Between Ad Creatives, Zapping Rates, and Ad Elasticities"
            ),
            "authors": [
                "Samsun Knight",
                "Gijs Overgoor",
                "Tsung Hsieh",
                "Yakov Bart",
            ],
            "status": "research_in_progress",
            "journal": None,
            "featured": True,
            "order": 50,
            "links": [
                ("SSRN", "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6110746"),
            ],
        },
        "project-skin-tone-diversity": {
            "title": (
                "Shades of Representation: Auto-Detection and Perception of "
                "Skin-Tone Diversity in Visual Marketing Communication"
            ),
            "authors": ["Wen Xie", "Gijs Overgoor", "H.H. Lee", "Z. Han"],
            "status": "research_in_progress",
            "journal": None,
            "featured": False,
            "order": 60,
            "links": [
                ("SSRN", "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4462296"),
            ],
        },
        "project-neuroad-video-understanding": {
            "title": "Neurosensory Response to Advertising",
            "authors": ["Gijs Overgoor", "Hang-Yee Chan"],
            "status": "research_in_progress",
            "journal": None,
            "featured": False,
            "order": 70,
            "links": [],
        },
    }

    assert publication_ids == {
        "pub-he-2022-fake-review-buyers",
        "pub-overgoor-2022-simplicity",
        "pub-overgoor-2019-ai-marketing",
        "proc-xie-2026-adsum",
        "proc-overgoor-2017-brand-popularity",
    }
    assert set(projects) == set(expected_projects)
    assert [project.order for project in snapshot.projects] == list(range(10, 71, 10))
    for project_id, expected in expected_projects.items():
        project = projects[project_id]
        assert project.title == expected["title"]
        assert project.authors == expected["authors"]
        assert project.status.value == expected["status"]
        assert project.journal == expected["journal"]
        assert project.featured is expected["featured"]
        assert project.order == expected["order"]
        assert [(link.label, str(link.url)) for link in project.links] == expected["links"]
        # Structural, not a pinned date: last_verified legitimately advances
        # on every content update.
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", project.last_verified) is not None
    assert pnas.author_note == "Authors listed in alphabetical order."
    assert buzzell.title == "Finalist, 2024 Robert D. Buzzell MSI Best Paper Award"
    assert buzzell.related_work_ids == [pnas.id]
    assert adsum.title == (
        "AdSum: Two-Stream Audio-Visual Summarization for Automated Video "
        "Advertisement Clipping"
    )
    assert adsum.authors == [
        "Wen Xie",
        "Yanjun Zhu",
        "Gijs Overgoor",
        "Yakov Bart",
        "Agata Lapedriza Garcia",
        "Sarah Ostadabbas",
    ]
    assert adsum.year == 2026
    assert adsum.journal == "International Conference on Multimedia Modeling"
    assert adsum.pages == "261–275"
    assert [(link.label, str(link.url)) for link in adsum.links] == [
        ("DOI", "https://doi.org/10.1007/978-981-95-6950-2_19"),
        ("arXiv", "https://arxiv.org/abs/2510.26569"),
    ]
    assert {
        media.id: media.related_work_ids for media in profile.media
    } == {
        "media-forbes-fake-reviews": [pnas.id],
        "media-wsj-fake-reviews": [pnas.id],
        "media-business-insider-images": ["pub-overgoor-2022-simplicity"],
        "media-upnext-social-images": ["pub-overgoor-2022-simplicity"],
        "media-ai-business-perfect-picture": ["pub-overgoor-2022-simplicity"],
    }
    assert profile.profile.email == "govergoor@smu.edu"
    assert profile.profile.portrait_alt == (
        "Gijs Overgoor, Assistant Professor of Marketing at SMU Cox School of Business"
    )
    presentations = {item.id: item.title for item in profile.presentations}
    assert presentations["talk-wisconsin-marketing-ai-2024"] == (
        "Symposium on Marketing AI at Wisconsin School of Business"
    )
    assert presentations["talk-ncsu-business-analytics-2023"] == (
        "NC State Business Analytics Initiative Roundtable"
    )
    assert presentations["talk-emac-ddc-2022"] == (
        "EMAC Annual Conference — Special Session for the Doctoral "
        "Dissertation Competition"
    )
    assert presentations["presentation-bizai-2024"] == "BizAI Conference"
    assert presentations["presentation-icmr-2017"] == (
        "International Conference on Multimedia Retrieval"
    )
    # Structural invariants only, not exact venue/year-set pins: which
    # presentations exist legitimately changes on every content update (a
    # new talk, a new year), so pinning exact sets here would break the
    # documented update -> approve -> push -> CI-deploy cycle the first
    # time a new talk is added. See the module docstring.
    assert any(item.kind == "invited_talk" for item in profile.presentations)
    assert any(item.kind == "conference_presentation" for item in profile.presentations)
    source_keys = [item.source_key for item in profile.presentations if item.source_key]
    assert len(source_keys) == len(set(source_keys))
    assert all(2015 <= item.year <= 2100 for item in profile.presentations)
    assert not {
        "Conference Presentation",
        "Invited Marketing Seminar",
        "Invited Talk",
    }.intersection(presentations.values())
    # No negative assertion on an excluded service-item id: profile.service
    # is built from an explicit curated snapshot, so absence of anything
    # not in that snapshot is structural.
    assert PHONE_PATTERN.search(all_text) is None
    assert "References" not in all_text
    assert "Matlab" not in all_text
    assert "Keras" not in all_text
    # No negative assertion on an excluded project title: the exact-set
    # assertion above (`set(projects) == set(expected_projects)`) already
    # guarantees no project outside expected_projects can appear.
    for private_token in (
        "next_action",
        "history",
        "target_journal",
        "candidate_journals",
        "overleaf_project",
        "/Users/",
        "Box-Box",
        "- [ ]",
    ):
        assert private_token not in all_text
    assert profile.technical_strengths[0].items == [
        "Python",
        "PyTorch",
        "statsmodels",
        "linearmodels",
        "PyFixest",
        "SQL",
    ]
    assert profile.industry == []
    assert profile.professional_services == (
        "I undertake consulting and expert witness work."
    )
    reviewer_service = next(
        item for item in profile.service if item.id == "service-ad-hoc-reviewer"
    )
    assert reviewer_service.details is not None
    assert "Marketing Science" in reviewer_service.details
    assert "Management Science" in reviewer_service.details


def test_job_market_body_text_matches_migration_hash() -> None:
    content_path = Path("content/job-market.md")
    expected_path = Path("tests/fixtures/job-market.sha256")
    digest = hashlib.sha256(
        _normalized_body_text(content_path.read_text(encoding="utf-8")).encode("utf-8")
    ).hexdigest()

    assert digest == expected_path.read_text(encoding="utf-8").strip()


def test_bio_supporting_copy_is_background_prose() -> None:
    bio = Path("content/bio.md").read_text(encoding="utf-8")
    normalized_bio = " ".join(bio.split())

    # Background now flows as part of About Me: no standalone headings.
    assert "## Background" not in bio
    assert "## Outside Work" not in bio
    # Personal "outside work" copy was removed entirely.
    assert "soccer" not in bio.lower()
    assert "dog" not in normalized_bio
    # Still no oversharing or project-note leakage.
    assert "dissertation" not in bio.lower()
    assert "AdNotator" not in bio
    assert "CrossFit" not in bio
    # Retains the factual academic background.
    assert "Rochester Institute of Technology" in normalized_bio
    assert "University of Amsterdam" in normalized_bio
