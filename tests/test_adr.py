from pathlib import Path

import pytest

from learning_curve.adr import next_number, render, slugify
from learning_curve.models import Decision
from tests.test_models import GOOD


def touch(directory: Path, *names: str) -> None:
    for name in names:
        (directory / name).touch()


def test_empty_or_missing_directory_starts_at_1(tmp_path: Path) -> None:
    assert next_number(tmp_path) == 1
    assert next_number(tmp_path / "nope") == 1


def test_numbering_continues_after_a_gap(tmp_path: Path) -> None:
    touch(tmp_path, "0001-a.md", "0004-b.md")
    assert next_number(tmp_path) == 5


def test_non_adr_files_are_ignored(tmp_path: Path) -> None:
    touch(tmp_path, "README.md", "0009.md", "12-x.md", "0007-x.txt", "0002-ok.md")
    assert next_number(tmp_path) == 3


@pytest.mark.parametrize(
    ("title", "slug"),
    [
        ("Use uv", "use-uv"),
        ("  Use   uv!! ", "use-uv"),
        ("Postgres vs. MySQL: pick one", "postgres-vs-mysql-pick-one"),
        ("!!!", "decision"),
        ("日本語", "decision"),
        ("a" * 80, "a" * 60),
        ("a" * 59 + " b", "a" * 59),
    ],
)
def test_slugify(title: str, slug: str) -> None:
    assert slugify(title) == slug


DECISION = Decision.model_validate(GOOD)


def test_render_frontmatter_and_sections() -> None:
    text = render(DECISION, 3)
    assert text.startswith(
        '---\nnumber: 3\ntitle: "Use uv"\ndate: 2026-11-18\nstatus: "provisional"\n'
    )
    assert 'source: {kind: "transcript", ref: "abc-123:L12"}' in text
    assert 'upgrade_trigger: "Revisit if uv install friction blocks users."' in text
    assert "# 0003. Use uv" in text
    assert "- **uv** (chosen): Fast, lockfile built in." in text
    assert "- **pip**: Ubiquitous, no lockfile." in text
    assert "## Upgrade trigger" in text


def test_render_omits_trigger_when_absent() -> None:
    payload = {**GOOD, "status": "accepted"}
    del payload["upgrade_trigger"]
    text = render(Decision.model_validate(payload), 1)
    assert "upgrade_trigger" not in text
    assert "## Upgrade trigger" not in text


def test_render_quotes_hostile_title() -> None:
    decision = Decision.model_validate({**GOOD, "title": 'Use uv: "fast"'})
    assert 'title: "Use uv: \\"fast\\""' in render(decision, 1)
