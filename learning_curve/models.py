"""Pydantic models for Claude's JSON output: the trust boundary before anything is written."""

import datetime as dt
import re
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    """Base model: unknown keys are errors and strings are trimmed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


NonEmpty = Annotated[str, Field(min_length=1)]
Status = (
    Literal["provisional", "accepted"] | Annotated[str, Field(pattern=r"^superseded-by-\d{4}$")]
)

# Full-match patterns per source kind. Transcript groups: 1 = start line, 2 = end line or None.
_REF_PATTERNS: dict[str, re.Pattern[str]] = {
    "transcript": re.compile(r"[\w-]+:L(\d+)(?:-(\d+))?"),
    "pr": re.compile(r"#\d+|https?://\S+"),
    "inferred": re.compile(r"[0-9a-fA-F]{4,40}(?:\s+[0-9a-fA-F]{4,40})*"),
}


class Option(Strict):
    """An alternative that was weighed."""

    name: NonEmpty
    summary: NonEmpty


class Source(Strict):
    """Evidence for a record.

    `ref` format depends on `kind`: `<session_id>:L<n>[-<m>]` for a transcript, `#42` or a URL
    for a pull request, one or more commit SHAs when inferred.
    """

    kind: Literal["transcript", "pr", "inferred"]
    ref: NonEmpty

    @model_validator(mode="after")
    def check_ref_matches_kind(self) -> Self:
        """Reject a `ref` that does not fit its `kind`, or a reversed line range."""
        match = _REF_PATTERNS[self.kind].fullmatch(self.ref)
        if not match:
            raise ValueError(f"ref {self.ref!r} is not a valid {self.kind} ref")
        if self.kind == "transcript" and match[2] and int(match[2]) < int(match[1]):
            raise ValueError(f"ref {self.ref!r} has its line range reversed")
        return self


class Decision(Strict):
    """An architecture decision record (ADR)."""

    title: NonEmpty
    date: dt.date
    status: Status
    context: NonEmpty
    options_considered: Annotated[list[Option], Field(min_length=2)]
    chosen: NonEmpty
    tradeoffs: NonEmpty
    upgrade_trigger: NonEmpty | None = None
    source: Source

    @model_validator(mode="after")
    def check_valid_chosen(self) -> Self:
        """Require `chosen` to name one of the options exactly."""
        if not any(option.name == self.chosen for option in self.options_considered):
            raise ValueError(f"chosen {self.chosen!r} is not a valid option")
        return self

    @model_validator(mode="after")
    def check_upgrade_trigger(self) -> Self:
        """Require `upgrade_trigger` for a provisional decision."""
        if self.status == "provisional" and self.upgrade_trigger is None:
            raise ValueError("upgrade_trigger is required when status is provisional")
        return self

    @model_validator(mode="after")
    def check_unique_option_names(self) -> Self:
        """Reject duplicate option names, which would make `chosen` ambiguous."""
        names = [option.name for option in self.options_considered]
        if len(names) != len(set(names)):
            raise ValueError("options_considered has duplicate names")
        return self


class Concept(Strict):
    """A concept, tradeoff or debug lesson learned during development; the input for quizzes."""

    title: NonEmpty
    kind: Literal["concept", "tradeoff", "debug"]
    explanation: Annotated[str, Field(min_length=1, max_length=600)]
    why_it_came_up: NonEmpty
    importance: Literal[1, 2, 3]
    session_ids: Annotated[list[NonEmpty], Field(min_length=1)]  # a concept can recur
    sources: Annotated[list[Source], Field(min_length=1)]
    alternatives: list[Option] = Field(default_factory=list)
    misconception: NonEmpty | None = None
    tags: list[NonEmpty] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_refs_cite_own_sessions(self) -> Self:
        """Require every transcript ref to name one of `session_ids`.

        Catches a ref from the wrong session, not a line that does not exist.
        """
        for source in self.sources:
            session = source.ref.split(":")[0]
            if source.kind == "transcript" and session not in self.session_ids:
                raise ValueError(f"ref {source.ref!r} is not from a session in session_ids")
        return self
