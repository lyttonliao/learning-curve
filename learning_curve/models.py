import datetime as dt
import re
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    """Base for every model here: unknown keys are errors, strings are trimmed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


NonEmpty = Annotated[str, Field(min_length=1)]
Status = (
    Literal["provisional", "accepted"]
    | Annotated[str, Field(pattern=r"^superseded-by-\d{4}$")]
)

_REF_PATTERNS: dict[str, re.Pattern[str]] = {
    "transcript": re.compile(r"[\w-]+:L\d+(?:-\d+)?"),
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
        """Reject a `ref` whose format does not match `kind`."""
        if not _REF_PATTERNS[self.kind].fullmatch(self.ref):
            raise ValueError(f"ref {self.ref!r} is not a valid {self.kind} ref")
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
