from pathlib import Path


def test_site_css_contains_approved_tokens_and_focus_state() -> None:
    css = Path("static/css/site.css").read_text(encoding="utf-8")
    assert "--paper: #f6f0e6" in css
    assert "--brick: #9b3f2f" in css
    assert ":focus-visible" in css
    assert "@media (max-width: 760px)" in css
    assert "clamp(2.1rem, 4.2vw, 3.25rem)" in css
    assert "clamp(1.45rem, 2.5vw, 1.85rem)" in css
    assert "h3 { font-size: 1.1rem; }" in css
    assert "5.8rem" not in css


def test_cv_css_preserves_resume_rules_and_safe_wrapping() -> None:
    css = Path("static/css/cv.css").read_text(encoding="utf-8")
    assert ".cv section > h2" in css
    assert "text-transform: uppercase" in css
    assert "overflow-wrap: anywhere" in css
    assert ".cv-dated" in css
    assert ".cv .citation" in css
    assert "max-width: none" in css
