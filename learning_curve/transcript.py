"""Digest of a Claude Code transcript: the conversation text, keyed by raw line for citations."""

import json
import re
import sys
from pathlib import Path
from typing import Any

_NOISE_PREFIXES = ("<command-name>", "<local-command")  # harness wrappers, not typed by anyone
_MAX_ENTRY = 8000  # guards against pasted logs; no real entry has exceeded 7,500 chars
_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)


def _text(content: str | list[dict[str, Any]]) -> str:
    """Return a message's text, dropping tool calls, tool results and thinking."""
    if isinstance(content, str):
        return content
    return "\n".join(b["text"] for b in content if b.get("type") == "text")


def _clip(text: str) -> str:
    """Shorten `text` to `_MAX_ENTRY` chars, keeping head and tail with a cut marker between.

    The tail is kept because long messages tend to end with their conclusion.
    """
    if len(text) <= _MAX_ENTRY:
        return text
    half = _MAX_ENTRY // 2
    return f"{text[:half]} [...cut {len(text) - _MAX_ENTRY} chars...] {text[-half:]}"


def digest(path: Path) -> str:
    """Return one `L<n> <role>: <text>` entry per user or assistant message.

    `n` is the line number in the transcript file, so `<session_id>:L<n>` cites the source.
    Entries are separated by a blank line; message text can contain blank lines too, so split
    on `\\n\\n(?=L\\d+ (?:user|assistant): )`.
    """
    out = []
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                # shortcut: a corrupt line is dropped silently (usually a half-written last
                # line); upgrade to a stderr warning if mid-file corruption shows up.
                continue
            if (
                entry.get("type") not in ("user", "assistant")
                or entry.get("isMeta")
                or entry.get("isCompactSummary")  # model-written summary, stored as a user turn
            ):
                continue
            text = _REMINDER.sub("", _text(entry["message"]["content"])).strip()
            if text and not text.startswith(_NOISE_PREFIXES):
                out.append(f"L{n} {entry['type']}: {_clip(text)}")
    return "\n\n".join(out)


def main(argv: list[str]) -> None:
    """Print the digest of the transcript file `argv[0]`."""
    print(digest(Path(argv[0])))


if __name__ == "__main__":
    main(sys.argv[1:])
