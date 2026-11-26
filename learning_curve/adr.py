"""Write validated decisions as numbered ADR files in `docs/decisions/`."""

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from learning_curve.cli import fail, load_decision
from learning_curve.models import Decision

_ADR_NAME = re.compile(r"(\d{4})-.+\.md")  # group 1: the ADR number
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_SLUG_MAX = 60


def next_number(directory: Path) -> int:
    """Return the next free ADR number in `directory`, starting at 1.

    Highest existing number plus one, not a count, so a gap never yields a taken number.
    Non-ADR files are ignored.
    """
    if not directory.is_dir():
        return 1
    numbers = [int(m[1]) for p in directory.iterdir() if (m := _ADR_NAME.fullmatch(p.name))]
    return max(numbers, default=0) + 1


def slugify(title: str) -> str:
    """Return a lowercase, hyphenated filename slug of at most 60 chars, or "untitled"."""
    # shortcut: ASCII only, so accented letters are dropped; upgrade if non-English titles matter.
    slug = _NON_ALNUM.sub("-", title.lower()).strip("-")[:_SLUG_MAX].strip("-")
    return slug or "untitled"


def yaml_str(text: str) -> str:
    """Quote `text` as a YAML scalar, so `:` or `"` cannot break frontmatter."""
    return json.dumps(text, ensure_ascii=False)  # a JSON string is valid YAML


def render(decision: Decision, number: int) -> str:
    """Render `decision` as a Markdown ADR with YAML frontmatter."""
    source = decision.source
    front = [
        "---",
        f"number: {number}",
        f"title: {yaml_str(decision.title)}",
        f"date: {decision.date.isoformat()}",
        f"status: {yaml_str(decision.status)}",
        f"source: {{kind: {yaml_str(source.kind)}, ref: {yaml_str(source.ref)}}}",
    ]
    if decision.upgrade_trigger is not None:
        front.append(f"upgrade_trigger: {yaml_str(decision.upgrade_trigger)}")
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
        decision.context,
        "",
        "## Options considered",
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
    """Write `decision` to `<root>/docs/decisions/NNNN-slug.md` and return the path.

    Raises:
        FileExistsError: the file exists; nothing is overwritten.
    """
    directory = root / "docs" / "decisions"
    directory.mkdir(parents=True, exist_ok=True)
    number = next_number(directory)
    path = directory / f"{number:04d}-{slugify(decision.title)}.md"
    # shortcut: concurrent writers can pick the same number; fine for a single-user CLI,
    # upgrade with a lock or a retry if that changes.
    with path.open("x", encoding="utf-8") as f:  # "x": create-or-fail in one step, no race
        f.write(render(decision, number))
    return path


def main(argv: Sequence[str]) -> int:
    """Write a Decision JSON payload (file or stdin) as an ADR and print its path.

    Returns 0 on success, 1 with JSON errors on bad input or a failed write. Invalid input
    creates nothing.
    """
    parser = argparse.ArgumentParser(description="Write a Decision JSON payload as an ADR.")
    parser.add_argument("file", nargs="?", help="JSON file; reads stdin if omitted")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="project root")
    args = parser.parse_args(argv)

    result = load_decision(args.file)
    if not isinstance(result, Decision):
        return fail(result)
    try:
        path = write_adr(result, args.root)
    except OSError as e:  # includes FileExistsError
        return fail([{"type": "io_error", "loc": [], "msg": str(e)}])

    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
