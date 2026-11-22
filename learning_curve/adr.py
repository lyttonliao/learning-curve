import json
import re
from pathlib import Path

from learning_curve.models import Decision

_ADR_NAME = re.compile(r"(\d{4})-.+\.md")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_SLUG_MAX = 60


def next_number(directory: Path) -> int:
    """
        Return the highest `NNNN-*.md` number in `directory plus 1.
        Gaps are allowed and other files are ignored. A missing directory counts 
        as empty, so the first ADR is 1.
    """
    if not directory.is_dir():
        return 1
    numbers = [int(m[1]) for p in directory.iterdir() if (m := _ADR_NAME.fullmatch(p.name))]
    return max(numbers, default=0) + 1


def slugify(title: str) -> str:
    """
        Turn a title into a lowercase, hyphen-separated filename slug (max 60 chars)

        Falls back to "decision" when nothing usable is left, e.g. for "!!!".
    """
    # shortcut: ASCII only, so accented letters are dropped; ugprade if non-English titles matter.
    slug = _NON_ALNUM.sub("-", title.lower()).strip("-")[:_SLUG_MAX].strip("-")
    return slug or "decision"


def _q(text: str) -> str:
    """
        Quote `text` as a YAML double-quoted scalar (a JSON string is valid YAML)
    """
    return json.dumps(text, ensure_ascii=False)


def render(decision: Decision, number: int) -> str:
    """
        Render `decision` as a Markdown ADR with YAML frontmatter.

        Every frontmatter string goes through `_q`, so characters like `:` or `:` in a title
        cannot break the YAML. The upgrade trigger is omitted when absent.
    """
    front = [
        "---",
        f"number: {number}",
        f"title: {_q(decision.title)}",
        f"date: {decision.date.isoformat()}",
        f"status: {_q(decision.status)}",
        f"source: {{kind: {_q(decision.source.kind)}, ref: {_q(decision.source.ref)}}}",
    ]
    if decision.upgrade_trigger is not None:
        front.append(f"upgrade_trigger: {_q(decision.upgrade_trigger)}")
    front.append("---")

    options = [
        f"- **{o.name}**{' (chosen)' if o.name == decision.chosen else ''}: {o.summary}"
        for o in decision.options_considered
    ]
    body = [
        f"# {number:04d}. {decision.title}",
        "",
        "## Context",
        "",
        "## Options Considered",
        "",
        *options,
        "",
        "## Decision",
        "",
        decision.chosen,
        "",
        "## Tradeoffs",
        "",
        decision.tradeoffs,
        "",
    ]
    if decision.upgrade_trigger is not None:
        body += ["## Upgrade trigger", "", decision.upgrade_trigger, ""]
    return "\n".join([*front, "", *body])


def write_adr(decision: Decision, root: Path) -> Path:
    """
        Write `decision` to `<root>/docs/decisions/NNNN-slug.md` and return the path.

        Opens the file in exclusive-create mode, so an existing file raises `FileExistsError`
        instead of being overwritten.
    """
    directory = root / "docs" / "decisions"
    directory.mkdir(parents=True, exist_ok=True)
    number = next_number(directory)
    path = directory / f"{number:04d}-{slugify(decision.title)}.md"
    # shortcut: two concurrent writers with different titles can both pick the same number;
    # fine for a single-user CLI, upgrade with a lock or a retry if that changes
    with path.open("x", encoding="utf-8") as f:
        f.write(render(decision, number))
    return path
