from pathlib import Path

import pytest

from learning_curve.concept import render_concept, write_concept
from learning_curve.models import Concept
from tests.test_models import CONCEPT_GOOD


def test_render_concept() -> None:
    out = render_concept(Concept.model_validate(CONCEPT_GOOD))
    assert out.startswith(
        '---\ntitle: "Lazy versus greedy regex"\nkind: "concept"\nimportance: 2\n'
    )
    assert 'sources: [{kind: "transcript", ref: "abc-123:L40-48"}]' in out
    assert "## Misconception" in out
    assert "## Alternatives" not in out


def test_render_concept_lists_alternatives() -> None:
    payload = {
        **CONCEPT_GOOD,
        "alternatives": [{"name": "greedy", "summary": "runs to the last tag"}],
    }
    assert "- **greedy**: runs to the last tag" in render_concept(Concept.model_validate(payload))


def test_write_concept_creates_note(tmp_path: Path) -> None:
    path = write_concept(Concept.model_validate(CONCEPT_GOOD), tmp_path)
    assert path == tmp_path / "docs" / "concepts" / "lazy-versus-greedy-regex.md"
    assert path.read_text(encoding="utf-8").startswith("---\ntitle:")


def test_write_concept_refuses_to_overwrite(tmp_path: Path) -> None:
    concept = Concept.model_validate(CONCEPT_GOOD)
    write_concept(concept, tmp_path)
    with pytest.raises(FileExistsError):
        write_concept(concept, tmp_path)
