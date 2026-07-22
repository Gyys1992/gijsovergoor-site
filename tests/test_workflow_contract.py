from pathlib import Path

import yaml


def test_pages_workflow_uses_snapshot_without_vault_access() -> None:
    workflow_path = Path(".github/workflows/pages.yml")
    text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)

    assert "Vault" not in text
    assert "actions/checkout@v6" in text
    assert "actions/setup-python@v6" in text
    assert "actions/configure-pages@v5" in text
    assert "actions/upload-pages-artifact@v4" in text
    assert "actions/deploy-pages@v4" in text
    assert workflow["permissions"]["pages"] == "write"
    assert workflow["permissions"]["id-token"] == "write"
