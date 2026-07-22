from pathlib import Path

from site_builder.config import load_config


def test_load_config_resolves_paths_from_repository_root(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "site.yaml").write_text(
        """
site:
  canonical_url: "https://www.gijsovergoor.com"
  routes: ["", "research", "cv", "job-market"]
paths:
  vault_root: "../Vault"
  public_profile: "tenure/public-profile.yaml"
  tenure_log: "tenure/log.md"
  projects: "research/projects"
  public_data: "data/public"
  output: "dist"
  templates: "templates"
  static: "static"
  content: "content"
release:
  external_link_timeout_seconds: 10
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_dir / "site.yaml")

    assert config.repository_root == tmp_path
    assert config.vault_root == tmp_path.parent / "Vault"
    assert config.public_profile == tmp_path.parent / "Vault/tenure/public-profile.yaml"
    assert config.routes == ("", "research", "cv", "job-market")
    assert config.canonical_url == "https://www.gijsovergoor.com"
