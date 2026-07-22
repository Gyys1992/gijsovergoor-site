from __future__ import annotations

import json
import logging
import re
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markdown_it import MarkdownIt

from site_builder.config import SiteConfig, load_config
from site_builder.models import (
    Presentation,
    PublicProject,
    PublicSnapshot,
    PublicStatus,
)

LOGGER = logging.getLogger(__name__)

STATUS_LABELS = {
    PublicStatus.REVISE_AND_RESUBMIT: "Revise and resubmit",
    PublicStatus.UNDER_REVIEW: "Under review",
    PublicStatus.PREPARING_RESUBMISSION: "In preparation for resubmission",
    PublicStatus.IN_PREPARATION: "In preparation",
    PublicStatus.RESEARCH_IN_PROGRESS: "Research in progress",
}


@dataclass(frozen=True)
class BuildResult:
    pages: tuple[Path, ...]
    output_dir: Path


def relative_url(current_route: str, target_route: str) -> str:
    prefix = "../" if current_route else ""
    return prefix if target_route == "" else f"{prefix}{target_route}/"


def asset_url(current_route: str, asset: str) -> str:
    prefix = "../" if current_route else ""
    return f"{prefix}static/{asset.lstrip('/')}"


def project_status_text(project: PublicProject) -> str:
    label = STATUS_LABELS[project.status]
    if project.journal is None:
        return label
    preposition = (
        "to"
        if project.status is PublicStatus.PREPARING_RESUBMISSION
        else "at"
    )
    return f"{label} {preposition} {project.journal}"


def human_join(values: Iterable[str]) -> str:
    items = list(dict.fromkeys(values))
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def presentation_label(presentation: Presentation) -> str:
    label = presentation.title
    if presentation.kind == "invited_talk":
        label = re.sub(r"^Invited Marketing Seminar at\s+", "", label)
        label = re.sub(r"\s+\((?:presented research|invited speaker)\)$", "", label)
    return label


def _load_snapshot(path: Path) -> PublicSnapshot:
    return PublicSnapshot.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )


def _write_redirect(
    config: SiteConfig,
    route: str,
    target: str,
    canonical: str,
) -> None:
    route_dir = config.output_dir / route
    route_dir.mkdir(parents=True, exist_ok=True)
    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="robots" content="noindex">
    <meta http-equiv="refresh" content="0; url={target}">
    <link rel="canonical" href="{canonical}">
    <title>Redirecting — Gijs Overgoor</title>
  </head>
  <body><p><a href="{target}">Continue to the updated page</a></p></body>
</html>
"""
    (route_dir / "index.html").write_text(html, encoding="utf-8")


def _relationships(
    snapshot: PublicSnapshot,
) -> tuple[dict[str, list[object]], dict[str, list[object]]]:
    media_by_work: dict[str, list[object]] = {}
    awards_by_work: dict[str, list[object]] = {}
    for mention in snapshot.profile.media:
        for work_id in mention.related_work_ids:
            media_by_work.setdefault(work_id, []).append(mention)
    for award in snapshot.profile.awards:
        for work_id in award.related_work_ids:
            awards_by_work.setdefault(work_id, []).append(award)
    return media_by_work, awards_by_work


def _environment(config: SiteConfig) -> Environment:
    environment = Environment(
        loader=FileSystemLoader(config.templates_dir),
        autoescape=select_autoescape(("html", "xml")),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.filters["tojson_pretty"] = lambda value: json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
    )
    environment.filters["human_join"] = human_join
    environment.filters["presentation_label"] = presentation_label
    return environment


def build_site(config: SiteConfig) -> BuildResult:
    snapshot = _load_snapshot(config.public_data_dir / "snapshot.yaml")
    markdown = MarkdownIt("commonmark", {"html": False})
    bio_html = markdown.render(
        (config.content_dir / "bio.md").read_text(encoding="utf-8")
    )
    job_market_html = markdown.render(
        (config.content_dir / "job-market.md").read_text(encoding="utf-8")
    )
    media_by_work, awards_by_work = _relationships(snapshot)
    if config.output_dir.exists():
        shutil.rmtree(config.output_dir)
    shutil.copytree(
        config.static_dir,
        config.output_dir / "static",
        dirs_exist_ok=True,
    )
    environment = _environment(config)
    page_specs = {
        "": (
            "home.html.j2",
            "Gijs Overgoor — Marketing, AI, and Visual Research",
            snapshot.profile.profile.short_positioning,
        ),
        "research": (
            "research.html.j2",
            "Research — Gijs Overgoor",
            "Publications and current research in visual marketing, advertising, "
            "AI, and platforms.",
        ),
        "cv": (
            "cv.html.j2",
            "Curriculum Vitae — Gijs Overgoor",
            "Academic curriculum vitae for Gijs Overgoor.",
        ),
        "job-market": (
            "job_market.html.j2",
            "Job Market — Gijs Overgoor",
            "Gijs Overgoor's preserved job-market essay.",
        ),
    }
    pages: list[Path] = []
    person_schema = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": snapshot.profile.profile.name,
        "url": config.canonical_url,
        "jobTitle": snapshot.profile.profile.title,
        "affiliation": {
            "@type": "Organization",
            "name": snapshot.profile.profile.institution,
        },
        "email": f"mailto:{snapshot.profile.profile.email}",
    }
    publication_schema = [
        {
            "@context": "https://schema.org",
            "@type": "ScholarlyArticle",
            "name": publication.title,
            "author": [
                {"@type": "Person", "name": author}
                for author in publication.authors
            ],
            "datePublished": str(publication.year),
            "isPartOf": {
                "@type": "Periodical",
                "name": publication.journal,
            },
            "url": (
                str(publication.links[0].url)
                if publication.links
                else f"{config.canonical_url}/research/"
            ),
        }
        for publication in snapshot.profile.publications
        if publication.category == "journal"
    ]
    for route, (template_name, title, description) in page_specs.items():
        route_dir = config.output_dir / route if route else config.output_dir
        route_dir.mkdir(parents=True, exist_ok=True)
        canonical = (
            f"{config.canonical_url}/"
            if route == ""
            else f"{config.canonical_url}/{route}/"
        )
        html = environment.get_template(template_name).render(
            route=route,
            title=title,
            description=description,
            canonical=canonical,
            profile=snapshot.profile,
            projects=snapshot.projects,
            bio_html=bio_html,
            job_market_html=job_market_html,
            media_by_work=media_by_work,
            awards_by_work=awards_by_work,
            project_status_text=project_status_text,
            person_schema=person_schema,
            publication_schema=publication_schema,
            url_for=lambda target, current=route: relative_url(current, target),
            static_url=lambda asset, current=route: asset_url(current, asset),
        )
        output_path = route_dir / "index.html"
        output_path.write_text(html, encoding="utf-8")
        pages.append(output_path)
    _write_redirect(
        config,
        "bio",
        "../#about",
        f"{config.canonical_url}/#about",
    )
    sitemap = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            *[
                (
                    f"  <url><loc>{config.canonical_url}/</loc></url>"
                    if route == ""
                    else f"  <url><loc>{config.canonical_url}/{route}/</loc></url>"
                )
                for route in config.routes
            ],
            "</urlset>",
            "",
        ]
    )
    (config.output_dir / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (config.output_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {config.canonical_url}/sitemap.xml\n",
        encoding="utf-8",
    )
    cname = config.repository_root / "CNAME"
    if cname.exists():
        shutil.copy2(cname, config.output_dir / "CNAME")
    return BuildResult(pages=tuple(pages), output_dir=config.output_dir)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = build_site(load_config())
    LOGGER.info("Built %d pages", len(result.pages))


if __name__ == "__main__":
    main()
