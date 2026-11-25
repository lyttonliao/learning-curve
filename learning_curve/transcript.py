import json
import sys
from pathlib import Path
from typing import Any

_NOISE_PREFIXES = (
    "<command-name>",
    "<local-command",
    "<system-reminder>",
    "This session is being continued", # compaction summary
)
_MAX_ENTRY = 2000


def _text(content: str | list[dict[str, Any]]) -> str:
    """Plain text of a message: a string as-is, or its `text` blocks joined by newlines."""
    if isinstance(content, str):
        return content
    return "\n".join(b["text"] for b in content if b.get("type") == "text")


def _clip(text: str) -> str:
    """Cut `text` to _MAX_ENTRY chars and say how many were dropped."""
    # shortcut: keeps the head only, so a conclusion at the end of a long message is lost;
    # upgrade to head+tail if extraction misses decisions stated at the end.
    if len(text) <= _MAX_ENTRY:
        return text
    return f"{text[:_MAX_ENTRY]} [...cut {len(text) - _MAX_ENTRY} chars]"


def digest(path: Path) -> str:
    """One `L<n> <role>: <text>` entry per conversation message; n is the raw file line.
    
    Entries are joined by a blank line, but message text can contain blank lines too, so split
    only on `\\n\\n(?=L\\d+ (?:user|assistant): )`.
    """
    out = []
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, start=1): # count before skipping: n must stay raw
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            # shortcut: silent skip, a corrupt mid-file line loses one entry unnoticed;
            # upgrade to a stderr warning with the line number if that ever bites.
            except json.JSONDecodeError:
                continue # partly written last line
            if (
                entry.get("type") not in ("user", "assistant") 
                or entry.get("isMeta")
                or entry.get("isCompactSummary")
            ):
                continue
            text = _text(entry["message"]["content"]).strip()
            if text and not text.startswith(_NOISE_PREFIXES): # tool-only turns have no text blocks
                out.append(f"L{n} {entry['type']}: {_clip(text)}")
    return "\n\n".join(out)


def main(argv: list[str]) -> None:
    """Print the digest of the transcript file named by argv[0]."""
    print(digest(Path(argv[0])))


if __name__ == "__main__":
    main(sys.argv[1:])