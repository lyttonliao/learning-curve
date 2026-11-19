from typing import Any

import pytest
from pydantic import ValidationError

from learning_curve.models import Decision, Source

GOOD: dict[str, Any] = {
    "title": "Use uv",
    "date": "2026-11-18",
    "status": "provisional",
    "context": "Need reproducible Python tooling.",
    "options_considered": [
        {"name": "uv", "summary": "Fast, lockfile built in."},
        {"name": "pip", "summary": "Ubiquitous, no lockfile."},
    ],
    "chosen": "uv",
    "tradeoffs": "Users must install uv.",
    "upgrade_trigger": "Revisit if uv install friction blocks users.",
    "source": {"kind": "transcript", "ref": "abc-123:L12"},
}


def test_good_payload_validates() -> None:
    assert Decision.model_validate(GOOD).chosen == "uv"


def test_accepted_without_trigger_validates() -> None:
    payload = {**GOOD, "status": "accepted"}
    del payload["upgrade_trigger"]
    Decision.model_validate(payload)


@pytest.mark.parametrize(
    "patch",
    [
        pytest.param({"extra": 1}, id="1-unknown-key"),
        pytest.param({"title": "   "}, id="2-blank-string"),
        pytest.param({"status": "superseded-by-12"}, id="3-bad-status"),
        pytest.param({"status": "done"}, id="3-unknown-status"),
        pytest.param(
            {"options_considered": [{"name": "uv", "summary": "s"}]},
            id="4-one-option",
        ),
        pytest.param(
            {"options_considered": [{"name": "uv"}, {"name": "pip"}]},
            id="4-option-missing-summary",
        ),
        pytest.param({"chosen": "poetry"}, id="5-chosen-not-an-option"),
        pytest.param({"chosen": "UV"}, id="5-chosen-case-differs"),
        pytest.param({"upgrade_trigger": None}, id="6-provisional-no-trigger"),
        pytest.param({"date": "2026-13-40"}, id="8-bad-date"),
    ],
)
def test_bad_payload_rejected(patch: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Decision.model_validate({**GOOD, **patch})


@pytest.mark.parametrize(
    ("kind", "ref"),
    [
        ("transcript", "abc-123:L12"),
        ("transcript", "abc:L12-30"),
        ("pr", "#42"),
        ("pr", "https://github.com/o/r/pull/42"),
        ("inferred", "A1b2c3d"),
        ("inferred", "a1b2 e4f5a6b"),
    ],
)
def test_source_good_refs(kind: str, ref: str) -> None:
    Source.model_validate({"kind": kind, "ref": ref})


@pytest.mark.parametrize(
    ("kind", "ref"),
    [
        ("transcript", "abc123"),
        ("transcript", "L12"),
        ("pr", "42"),
        ("inferred", "abc"),
        ("inferred", "hello"),
        ("inferred", "a1b2,e4f5"),
        ("bogus", "x"),
    ],
)
def test_source_bad_refs(kind: str, ref: str) -> None:
    with pytest.raises(ValidationError):
        Source.model_validate({"kind": kind, "ref": ref})
