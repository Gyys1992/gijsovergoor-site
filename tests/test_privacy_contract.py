"""Independent privacy audit of every surface that reaches GitHub Pages,
plus a repo-wide guard so a private literal committed to *any* tracked
source file cannot slip past runtime-only scan coverage.

This module is deliberately decoupled from site_builder.sync.scan_public_text /
FORBIDDEN_PUBLIC_TOKENS: it re-declares its own forbidden-token list so a
future change that weakens the internal scan cannot silently weaken this
outer contract check too. test_public_surfaces_contain_no_forbidden_private_tokens
scans the repository-relative directories that are always present
(data/public, content, templates, static) plus dist, but only if dist has
already been built — CI runs pytest before the build step, so dist will not
exist yet in that context.

test_every_git_tracked_text_file_is_free_of_forbidden_private_literals below
is the repo-wide guard: a whole-branch review found real private literals
(a phone number, a private project title) committed directly into tracked
source files that no runtime-path scan would ever see, because they never
reach a deployed or generated surface in the first place. It scans every
git-tracked text file instead of just the always-scanned directories, so
that class of finding cannot recur silently.
"""

import subprocess
from pathlib import Path

from site_builder.validate import PHONE_PATTERN

REPO_ROOT = Path(__file__).resolve().parent.parent

# Independent copy of site_builder.sync.FORBIDDEN_PUBLIC_TOKENS on purpose
# (see module docstring above), aligned to be a superset check against it.
FORBIDDEN_TOKENS = (
    "/Users/",
    "next_action",
    "history",
    "target_journal",
    "candidate_journals",
    "overleaf_project",
    "Box-Box",
    "- [ ]",
)

# The subset of FORBIDDEN_TOKENS that is never legitimate in ANY tracked
# file, fixture or not: unlike the field-name tokens below, these get no
# tests/fixtures/** exemption in the repo-wide scan. The mandatory-
# separator PHONE_PATTERN (imported from site_builder.validate) is checked
# alongside these with the same no-fixture-exemption rule.
ABSOLUTE_TOKENS = ("/Users/", "Box-Box")

# The remaining tokens: task/journal-tracking field names from the private
# Vault's frontmatter schema, plus markdown checkbox syntax used in private
# planning notes. These are innocuous-looking identifiers that are private
# markers only in the context of the private Vault, so synthetic fixtures
# and tests that exercise the scrubbing contract are allowed to contain
# them by design.
FIELD_NAME_TOKENS = tuple(token for token in FORBIDDEN_TOKENS if token not in ABSOLUTE_TOKENS)

# Text suffixes only: static/images contains a .jpg whose raw bytes are not
# valid UTF-8 and must never be decoded or scanned.
TEXT_SUFFIXES = {
    ".md",
    ".yaml",
    ".yml",
    ".css",
    ".html",
    ".j2",
    ".txt",
    ".py",
    ".xml",
    ".json",
    ".svg",
}

# config/site.yaml is deliberately excluded: it legitimately contains the
# repository-relative Vault path "../Vault", which never reaches a deployed
# or generated surface.
ALWAYS_SCANNED_DIRS = ("data/public", "content", "templates", "static")

# Files that structurally must contain the literal token strings themselves
# in order to declare or assert the privacy contract — exempt from BOTH
# token tiers in the repo-wide scan below (none of the three legitimately
# contains "/Users/" or "Box-Box" as leaked data; each contains them only
# as part of a token-list declaration or an absence assertion against the
# real snapshot).
SELF_DECLARING_TOKEN_FILES = frozenset(
    {
        "site_builder/sync.py",  # declares FORBIDDEN_PUBLIC_TOKENS
        "tests/test_privacy_contract.py",  # this module: declares FORBIDDEN_TOKENS above
        "tests/test_content_contract.py",  # asserts all 8 tokens absent from the real snapshot
    }
)

# Files exempt from the FIELD-NAME tier only (never the absolute tier):
# each references a field-name token as part of testing or reporting on
# the scrubbing contract itself, not as leaked private data. Audited via
# `git grep` for every FIELD_NAME_TOKENS entry across all tracked files —
# this is the complete list beyond SELF_DECLARING_TOKEN_FILES and
# tests/fixtures/**.
FIELD_NAME_TOKEN_ADDITIONAL_EXEMPT_FILES = frozenset(
    {
        # Reads the private Vault frontmatter field `target_journal` by
        # name to render review/project-publication-decisions.md, which is
        # gitignored and never a public-reaching surface.
        "site_builder/candidates.py",
        # Injects the literal string "next_action" into rendered output to
        # prove validate_site's forbidden-token scan actually rejects it.
        "tests/test_validate.py",
        # Asserts the strict pydantic schema rejects an unknown
        # "target_journal" field — the point of the test is the literal.
        "tests/test_models.py",
        # Asserts a synthetic fixture's private "history"-containing value
        # does not survive extraction.
        "tests/test_projects.py",
        # Asserts "target_journal" / a synthetic "history"-containing
        # value do not survive sync.
        "tests/test_sync.py",
        # Embeds an inline synthetic frontmatter fixture (target_journal)
        # to prove the candidate report never reaches data/public.
        "tests/test_candidates.py",
    }
)


def _text_files(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix in TEXT_SUFFIXES
    )


def test_public_surfaces_contain_no_forbidden_private_tokens() -> None:
    directories = [Path(name) for name in ALWAYS_SCANNED_DIRS]
    for directory in directories:
        assert directory.exists(), f"expected always-scanned directory to exist: {directory}"
    dist = Path("dist")
    if dist.exists():
        directories.append(dist)

    scanned_files = [path for directory in directories for path in _text_files(directory)]
    assert scanned_files, "expected at least one text file to scan"

    for path in scanned_files:
        text = path.read_text(encoding="utf-8")
        found = [token for token in FORBIDDEN_TOKENS if token in text]
        assert not found, f"{path} contains forbidden tokens: {found}"
        phone_match = PHONE_PATTERN.search(text)
        assert phone_match is None, f"{path} contains a phone-shaped number"


def _tracked_text_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted(
        line for line in result.stdout.splitlines() if line and Path(line).suffix in TEXT_SUFFIXES
    )


def test_every_git_tracked_text_file_is_free_of_forbidden_private_literals() -> None:
    """Repo-wide guard: unlike the directory-scoped test above, this scans
    every git-tracked text file regardless of whether it reaches the
    deployed site — catching a private literal sitting in tracked source
    (a committed test assertion, a docs/ file, ...) that no runtime-path
    scan would ever see.
    """
    tracked_text_files = _tracked_text_files()
    assert tracked_text_files, "expected at least one git-tracked text file"

    failures: list[str] = []
    for relative_path in tracked_text_files:
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        is_fixture = relative_path.startswith("tests/fixtures/")
        is_self_declaring = relative_path in SELF_DECLARING_TOKEN_FILES

        if not is_self_declaring:
            for token in ABSOLUTE_TOKENS:
                if token in text:
                    failures.append(f"{relative_path}: forbidden absolute token {token!r}")
            phone_match = PHONE_PATTERN.search(text)
            if phone_match:
                failures.append(f"{relative_path}: phone-shaped number")

        field_name_exempt = (
            is_fixture
            or is_self_declaring
            or relative_path in FIELD_NAME_TOKEN_ADDITIONAL_EXEMPT_FILES
        )
        if not field_name_exempt:
            for token in FIELD_NAME_TOKENS:
                if token in text:
                    failures.append(f"{relative_path}: forbidden field-name token {token!r}")

    assert not failures, "forbidden private literal(s) found:\n" + "\n".join(failures)
