import datetime as dt
import re
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    """Base for every model here: unknown keys are errors, strings are trimmed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


NonEmpty = Annotated[str, Field(min_length=1)]
Status = (
    Literal["provisional", "accepted"] | Annotated[str, Field(pattern=r"^superseded-by-\d{4}$")]
)

# Matched with fullmatch, so each pattern must cover the whole ref.
# transcript: `<session_id>:L<start>` or `<session_id>:L<start>-<end>`. Group 1 is the start
# line, group 2 the end line (None for a single line). `(?:...)` keeps the optional range
# from taking a group number of its own.
_REF_PATTERNS: dict[str, re.Pattern[str]] = {
    "transcript": re.compile(r"[\w-]+:L(\d+)(?:-(\d+))?"),
    "pr": re.compile(r"#\d+|https?://\S+"),
    "inferred": re.compile(r"[0-9a-fA-F]{4,40}(?:\s+[0-9a-fA-F]{4,40})*"),
}


class Option(Strict):
    """One alternative that was weighed before choosing."""

    name: NonEmpty
    summary: NonEmpty


class Source(Strict):
    """Where the evidence for a decision lives.

    `kind` picks the format `ref` must have: a transcript line range, a pull
    request, or one or more commit SHAs (when the decision was inferred).
    """

    kind: Literal["transcript", "pr", "inferred"]
    ref: NonEmpty

    @model_validator(mode="after")
    def check_ref_matches_kind(self) -> Self:
        """Reject a `ref` whose format does not match `kind`.

        A transcript range must not be reversed (`L30-12`); a one-line range
        (`L12-12`) is allowed.
        """
        match = _REF_PATTERNS[self.kind].fullmatch(self.ref)
        if not match:
            raise ValueError(f"ref {self.ref!r} is not a valid {self.kind} ref")
        if self.kind == "transcript" and match[2] and int(match[2]) < int(match[1]):
            raise ValueError(f"ref {self.ref!r} has its line range reversed")
        return self


class Decision(Strict):
    """One architecture decision record (ADR), validated before anything is written.

    Claude produces this as JSON, so the model is the trust boundary: nothing
    reaches disk unless it passes every rule below.
    """

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
        """Require `chosen` to equal one option's name exactly (case-sensitive)."""
        if not any(option.name == self.chosen for option in self.options_considered):
            raise ValueError(f"chosen {self.chosen!r} is not a valid option")
        return self

    @model_validator(mode="after")
    def check_upgrade_trigger(self) -> Self:
        """Require `upgrade_trigger` when the decision is provisional."""
        if self.status == "provisional" and self.upgrade_trigger is None:
            raise ValueError("upgrade_trigger is required when status is provisional")
        return self

    @model_validator(mode="after")
    def check_unique_option_names(self) -> Self:
        """Reject two options with the same name (exact match like 'chosen')."""
        names = [option.name for option in self.options_considered]
        if len(names) != len(set(names)):
            raise ValueError("options_considered has duplicate names")
        return self


class Concept(Strict):
    """One thing learned along the way, validated before it is written.
    
    Quizzes and prose are generated from these, never from raw transcripts.
    """

    title: NonEmpty
    kind: Literal["concept", "tradeoff", "debug"]
    explanation: Annotated[str, Field(min_length=1, max_length=600)]
    why_it_came_up: NonEmpty
    importance: Literal[1, 2, 3]
    session_id: NonEmpty
    sources: Annotated[list[Source], Field(min_length=1)]
    alternatives: list[Option] = Field(default_factory=list)
    misconception: NonEmpty | None = None
    tags: list[NonEmpty] = Field(default_factory=list)