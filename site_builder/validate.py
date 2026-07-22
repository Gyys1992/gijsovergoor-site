from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from site_builder.config import SiteConfig, load_config
from site_builder.sync import scan_public_text

LOGGER = logging.getLogger(__name__)

# Separators between digit groups are mandatory: a bare 10-digit run (e.g.
# the DOI fragment "pnas.2211932119" that legitimately appears in a link
# URL) must never false-positive as a phone number.
PHONE_PATTERN = re.compile(r"\b\d{3}[ .\-]\d{3}[ .\-]\d{4}\b")


@dataclass(frozen=True)
class ValidationReport:
    routes: tuple[str, ...]
    checked_files: int
    errors: tuple[str, ...]


def _route_file(config: SiteConfig, route: str) -> Path:
    return (
        config.output_dir / "index.html"
        if route == ""
        else config.output_dir / route / "index.html"
    )


def _resolve_internal(page: Path, href: str, output_dir: Path) -> Path:
    clean = urlsplit(href).path
    candidate = (page.parent / clean).resolve()
    if clean.endswith("/") or candidate.is_dir():
        candidate = candidate / "index.html"
    if output_dir.resolve() not in candidate.parents and candidate != output_dir.resolve():
        raise ValueError(f"internal link leaves output directory: {href}")
    return candidate


def _is_redirect_stub(soup: BeautifulSoup) -> bool:
    """True for the noindex meta-refresh stub build_site writes for
    superseded routes (currently /bio; see build.py's _write_redirect).

    Stubs intentionally skip the shared base template, so they carry none
    of the navigation chrome, canonical/description/og metadata, or
    structured data that page-level checks below look for. They are exempt
    from those checks, but still go through the forbidden-token privacy
    scan and internal link/asset resolution like every other generated
    page — a redirect stub is exactly the kind of low-traffic page where a
    stray private token or dangling link is easy to miss by hand.
    """
    robots = soup.select_one('meta[name="robots"]')
    has_noindex = robots is not None and "noindex" in str(robots.get("content", "")).lower()
    has_refresh = soup.select_one('meta[http-equiv="refresh"]') is not None
    return has_noindex and has_refresh


def validate_site(config: SiteConfig) -> ValidationReport:
    errors: list[str] = []
    html_files = sorted(config.output_dir.rglob("*.html"))
    route_files = {_route_file(config, route) for route in config.routes}
    for route_file in route_files:
        if not route_file.exists():
            errors.append(f"missing route file: {route_file}")

    cv_file = _route_file(config, "cv")
    cv_text: str | None = None
    combined_parts: list[str] = []
    for page in html_files:
        text = page.read_text(encoding="utf-8")
        combined_parts.append(text)
        if page == cv_file:
            cv_text = text
        scan_public_text(text, str(page))
        soup = BeautifulSoup(text, "html.parser")
        if not _is_redirect_stub(soup):
            if soup.select_one("main") is None:
                errors.append(f"{page}: missing main landmark")
            if soup.select_one('a[href="#main"]') is None:
                errors.append(f"{page}: missing skip link")
            canonical = soup.select_one('link[rel="canonical"]')
            if canonical is None or not canonical.get("href", "").startswith(
                config.canonical_url
            ):
                errors.append(f"{page}: missing canonical URL")
            if soup.select_one('meta[name="description"]') is None:
                errors.append(f"{page}: missing description")
            for property_name in ("og:title", "og:description", "og:url"):
                if soup.select_one(f'meta[property="{property_name}"]') is None:
                    errors.append(f"{page}: missing {property_name}")
            if soup.select_one('script[type="application/ld+json"]') is None:
                errors.append(f"{page}: missing structured data")
        for image in soup.select("img"):
            if not str(image.get("alt", "")).strip():
                errors.append(f"{page}: image is missing alt text")
        for element in soup.select("[href], [src]"):
            attribute = "href" if element.has_attr("href") else "src"
            href = str(element[attribute])
            if href.startswith(
                ("http://", "https://", "mailto:", "tel:", "#", "data:")
            ):
                continue
            target = _resolve_internal(page, href, config.output_dir)
            if not target.exists():
                errors.append(f"{page}: broken internal link or asset {href}")

    combined = "\n".join(combined_parts)
    if PHONE_PATTERN.search(combined):
        errors.append("output contains a phone-shaped number")
    if cv_text is not None and ">References<" in cv_text:
        errors.append("CV contains the removed References section")

    if errors:
        raise ValueError("site validation failed:\n" + "\n".join(errors))
    LOGGER.info("Validated %d HTML files", len(html_files))
    return ValidationReport(
        routes=config.routes,
        checked_files=len(html_files),
        errors=(),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    validate_site(load_config())


if __name__ == "__main__":
    main()
