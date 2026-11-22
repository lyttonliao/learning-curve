import re
from pathlib import Path

_ADR_NAME = re.compile(r"(\d{4})-.+\.md")


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

