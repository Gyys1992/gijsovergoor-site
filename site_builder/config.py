from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SiteConfig:
    repository_root: Path
    canonical_url: str
    routes: tuple[str, ...]
    vault_root: Path
    public_profile: Path
    tenure_log: Path
    projects_dir: Path
    public_data_dir: Path
    output_dir: Path
    templates_dir: Path
    static_dir: Path
    content_dir: Path
    external_link_timeout_seconds: float


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a YAML mapping")
    return value


def load_config(path: Path = Path("config/site.yaml")) -> SiteConfig:
    config_path = path.resolve()
    repository_root = config_path.parent.parent
    raw = _mapping(yaml.safe_load(config_path.read_text(encoding="utf-8")), "config")
    site = _mapping(raw.get("site"), "site")
    paths = _mapping(raw.get("paths"), "paths")
    release = _mapping(raw.get("release"), "release")
    vault_root = (repository_root / str(paths["vault_root"])).resolve()

    return SiteConfig(
        repository_root=repository_root,
        canonical_url=str(site["canonical_url"]).rstrip("/"),
        routes=tuple(str(route) for route in site["routes"]),
        vault_root=vault_root,
        public_profile=(vault_root / str(paths["public_profile"])).resolve(),
        tenure_log=(vault_root / str(paths["tenure_log"])).resolve(),
        projects_dir=(vault_root / str(paths["projects"])).resolve(),
        public_data_dir=(repository_root / str(paths["public_data"])).resolve(),
        output_dir=(repository_root / str(paths["output"])).resolve(),
        templates_dir=(repository_root / str(paths["templates"])).resolve(),
        static_dir=(repository_root / str(paths["static"])).resolve(),
        content_dir=(repository_root / str(paths["content"])).resolve(),
        external_link_timeout_seconds=float(
            release["external_link_timeout_seconds"]
        ),
    )
