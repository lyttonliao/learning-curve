from learning_curve.concept import render_concept
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
