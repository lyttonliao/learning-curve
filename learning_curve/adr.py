import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from learning_curve.cli import fail, load_decision
from learning_curve.models import Decision

# Group 1 is the 4-digit number. Used with fullmatch, so README.md and 0009.md are ignored.
_ADR_NAME = re.compile(r"(\d{4})-.+\.md")
# Any run of other characters becomes a single hyphen.
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_SLUG_MAX = 60


def next_number(directory: Path) -> int:
    """Return the highest `NNNN-*.md` number in `directory` plus 1.

    Highest, not a count, so a gap (0001, 0004) never produces a number already taken.
    Other files are ignored. A missing directory counts as empty, so the first ADR is 1.
    """
    if not directory.is_dir():
        return 1
    # `:=` binds the match so fullmatch runs once per file.
    numbers = [int(m[1]) for p in directory.iterdir() if (m := _ADR_NAME.fullmatch(p.name))]
    return max(numbers, default=0) + 1


def slugify(title: str) -> str:
    """Turn a title into a lowercase, hyphen-separated filename slug (max 60 chars).

    Falls back to "decision" when nothing usable is left, e.g. for "!!!".
    """
    # shortcut: ASCII only, so accented letters are dropped; upgrade if non-English titles matter.
    # Strip again after the cut: it can leave a trailing hyphen.
    slug = _NON_ALNUM.sub("-", title.lower()).strip("-")[:_SLUG_MAX].strip("-")
    return slug or "decision"


def _q(text: str) -> str:
    """Quote `text` as a YAML double-quoted scalar (a JSON string is valid YAML)."""
    return json.dumps(text, ensure_ascii=False)


def render(decision: Decision, number: int) -> str:
    """Render `decision` as a Markdown ADR with YAML frontmatter.

    Every frontmatter string goes through `_q`, so characters like `:` or `"` in a title
    cannot break the YAML. The upgrade trigger is omitted when absent.
    """
    front = [
        "---",
        f"number: {number}",
        f"title: {_q(decision.title)}",
        f"date: {decision.date.isoformat()}",
        f"status: {_q(decision.status)}",
        # Single-line YAML mapping; the doubled braces are literal braces in the f-string.
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

    Never overwrites: mode "x" creates the file only if it does not exist, in one OS call,
    and raises `FileExistsError` otherwise. A separate `exists()` check could race.
    """
    directory = root / "docs" / "decisions"
    directory.mkdir(parents=True, exist_ok=True)
    number = next_number(directory)
    path = directory / f"{number:04d}-{slugify(decision.title)}.md"
    # shortcut: two concurrent writers with different titles can both pick the same number;
    # fine for a single-user CLI, upgrade with a lock or a retry if that changes.
    with path.open("x", encoding="utf-8") as f:
        f.write(render(decision, number))
    return path


def main(argv: Sequence[str]) -> int:
    """Write one Decision JSON payload as an ADR and print the path.

    Reads the payload from the file in `argv`, or from stdin. Valid: prints the written
    path, returns 0. Invalid or unwritable: prints errors as JSON, returns 1. Validation
    happens before `write_adr`, so invalid input creates no files or directories.
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
