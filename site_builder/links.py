from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
import yaml

from site_builder.config import SiteConfig, load_config
from site_builder.models import PublicSnapshot

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LinkIssue:
    url: str
    detail: str


@dataclass(frozen=True)
class LinkReport:
    checked: int
    warnings: tuple[LinkIssue, ...]


def _urls(snapshot: PublicSnapshot) -> list[str]:
    links = list(snapshot.profile.profile.links)
    for publication in snapshot.profile.publications:
        links.extend(publication.links)
    for project in snapshot.projects:
        links.extend(project.links)
    urls = [str(link.url) for link in links]
    urls.extend(str(mention.url) for mention in snapshot.profile.media)
    return sorted(set(urls))


def check_external_links(config: SiteConfig) -> LinkReport:
    snapshot = PublicSnapshot.model_validate(
        yaml.safe_load(
            (config.public_data_dir / "snapshot.yaml").read_text(encoding="utf-8")
        )
    )
    urls = _urls(snapshot)
    warnings: list[LinkIssue] = []
    with httpx.Client(
        follow_redirects=True,
        timeout=config.external_link_timeout_seconds,
        headers={"User-Agent": "gijsovergoor-site-link-check/1.0"},
    ) as client:
        for url in urls:
            try:
                response = client.get(url)
                if response.status_code >= 400:
                    warnings.append(
                        LinkIssue(url=url, detail=f"HTTP {response.status_code}")
                    )
            except httpx.HTTPError as error:
                warnings.append(LinkIssue(url=url, detail=type(error).__name__))
    for warning in warnings:
        LOGGER.warning("%s — %s", warning.url, warning.detail)
    return LinkReport(checked=len(urls), warnings=tuple(warnings))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = check_external_links(load_config())
    LOGGER.info(
        "Checked %d external links with %d warnings",
        report.checked,
        len(report.warnings),
    )


if __name__ == "__main__":
    main()
