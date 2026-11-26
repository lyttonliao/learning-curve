from typing import Any

import pytest
from pydantic import ValidationError

from learning_curve.models import Concept, Decision, Source

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


def test_good_payload_round_trips() -> None:
    # mode="json" turns `date` into its ISO string; plain model_dump() keeps a `date` object.
    assert Decision.model_validate(GOOD).model_dump(mode="json") == GOOD


@pytest.mark.parametrize("status", ["accepted", "superseded-by-0012"])
def test_no_trigger_needed_unless_provisional(status: str) -> None:
    payload = {**GOOD, "status": status}
    del payload["upgrade_trigger"]
    Decision.model_validate(payload)


def failing(payload: dict[str, Any]) -> list[tuple[tuple[int | str, ...], str]]:
    """Validate `payload`, expect failure, return (loc, msg) for each error."""
    with pytest.raises(ValidationError) as exc:
        Decision.model_validate(payload)
    return [(e["loc"], e["msg"]) for e in exc.value.errors()]


@pytest.mark.parametrize(
    ("patch", "loc", "msg"),
    [
        pytest.param({"extra": 1}, ("extra",), "", id="1-unknown-key"),
        pytest.param({"title": "    "}, ("title",), "", id="2-blank-title"),
        pytest.param({"context": " "}, ("context",), "", id="2-blank-context"),
        pytest.param({"tradeoffs": ""}, ("tradeoffs",), "", id="2-blank-tradeoffs"),
        pytest.param({"chosen": ""}, ("chosen",), "", id="2-blank-chosen"),
        pytest.param({"upgrade_trigger": " "}, ("upgrade_trigger",), "", id="2-blank-trigger"),
        pytest.param(
            {"options_considered": [{"name": " ", "summary": "s"}, GOOD["options_considered"][1]]},
            ("options_considered", 0, "name"),
            "",
            id="2-blank-option-name",
        ),
        pytest.param(
            {"source": {"kind": "pr", "ref": " "}},
            ("source", "ref"),
            "",
            id="2-blank-source-ref",
        ),
        pytest.param({"status": "superseded-by-12"}, ("status",), "", id="3-bad-status"),
        pytest.param({"status": "done"}, ("status",), "", id="3-unknown-status"),
        pytest.param(
            {"options_considered": [{"name": "uv", "summary": "s"}]},
            ("options_considered",),
            "",
            id="4-one-option",
        ),
        pytest.param(
            {"options_considered": [{"name": "uv"}, {"name": "pip"}]},
            ("options_considered", 0, "summary"),
            "",
            id="4-option-missing-summary",
        ),
        pytest.param(
            {
                "options_considered": [
                    {"name": "uv", "summary": "a"},
                    {"name": "uv", "summary": "b"},
                ],
            },
            (),
            "duplicate",
            id="4-duplicate-option-names",
        ),
        pytest.param({"chosen": "poetry"}, (), "not a valid option", id="5-chosen-not-an-option"),
        pytest.param({"chosen": "UV"}, (), "not a valid option", id="5-chosen-case-differs"),
        pytest.param(
            {"upgrade_trigger": None},
            (),
            "upgrade_trigger is required",
            id="6-provisional-no-trigger",
        ),
        pytest.param({"date": "2026-13-40"}, ("date",), "", id="8-bad-date"),
    ],
)
def test_bad_payload_rejected(patch: dict[str, Any], loc: tuple[int | str, ...], msg: str) -> None:
    # Field errors have a `loc` like ("title",); model_validator errors have loc == (),
    # so those cases match on `msg` instead. `loc` is compared as a prefix because a union
    # field like `status` appends the failing branch to it.
    errors = failing({**GOOD, **patch})
    assert any(e_loc[: len(loc)] == loc and msg in e_msg for e_loc, e_msg in errors)


@pytest.mark.parametrize(
    ("kind", "ref"),
    [
        ("transcript", "abc-123:L12"),
        ("transcript", "abc:L12-30"),
        ("transcript", "abc:L12-12"),
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
        ("transcript", "abc:L12-"),
        ("transcript", "abc:L"),
        ("pr", "42"),
        ("inferred", "abc"),
        ("inferred", "hello"),
        ("inferred", "a1b2,e4f5"),
    ],
)
def test_source_bad_refs(kind: str, ref: str) -> None:
    with pytest.raises(ValidationError, match="not a valid"):
        Source.model_validate({"kind": kind, "ref": ref})


def test_source_reversed_range_rejected() -> None:
    with pytest.raises(ValidationError, match="reversed"):
        Source.model_validate({"kind": "transcript", "ref": "abc:L30-12"})


def test_source_unknown_kind_rejected() -> None:
    with pytest.raises(ValidationError, match="kind"):
        Source.model_validate({"kind": "bogus", "ref": "x"})


CONCEPT_GOOD: dict[str, Any] = {
    "title": "Lazy versus greedy regex",
    "kind": "concept",
    "explanation": "`.*?` stops at the first closing tag; `.*` runs to the last one.",
    "why_it_came_up": "Stripping system-reminder blocks from the digest.",
    "importance": 2,
    "session_ids": ["abc-123"],
    "sources": [{"kind": "transcript", "ref": "abc-123:L40-48"}],
    "alternatives": [],
    "misconception": "Thought `.*` needed a match, so empty blocks would fail.",
    "tags": ["regex"],
}


def test_concept_round_trips() -> None:
    assert Concept.model_validate(CONCEPT_GOOD).model_dump(mode="json") == CONCEPT_GOOD


@pytest.mark.parametrize(
    ("patch", "loc"),
    [
        ({"importance": 4}, ("importance",)),
        ({"kind": "idea"}, ("kind",)),
        ({"sources": []}, ("sources",)),
        ({"session_ids": []}, ("session_ids",)),
        ({"explanation": "x" * 601}, ("explanation",)),
    ],
)
def test_concept_rejects(patch: dict[str, Any], loc: tuple[str, ...]) -> None:
    with pytest.raises(ValidationError) as exc:
        Concept.model_validate({**CONCEPT_GOOD, **patch})
    assert [e["loc"] for e in exc.value.errors()] == [loc]


def test_concept_rejects_ref_from_another_session() -> None:
    payload = {**CONCEPT_GOOD, "sources": [{"kind": "transcript", "ref": "xyz-999:L5"}]}
    with pytest.raises(ValidationError, match="not from a session in session_ids"):
        Concept.model_validate(payload)
