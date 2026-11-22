import re
from pathlib import Path

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
