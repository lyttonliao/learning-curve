import json
from pathlib import Path

from learning_curve.transcript import _clip, _text, digest


def test_text_string_passes_through() -> None:
    assert _text("hi") == "hi"


def test_text_keeps_only_text_blocks() -> None:
    blocks = [
        {"type": "thinking", "thinking": "hmm"},
        {"type": "text", "text": "a"},
        {"type": "tool_use", "name": "Bash"},
        {"type": "text", "text": "b"}
    ]
    assert _text(blocks) == "a\nb"


def test_digest_numbers_by_raw_line(tmp_path: Path) -> None:
    lines = [
        {"type": "mode"},
        {"type": "user", "message": {"content": "why dict?"}},
        {"type": "api-request"},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "0(1) lookup"}]}},
    ]
    f = tmp_path / "s.jsonl"
    f.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
    assert digest(f) == "L2 user: why dict?\n\nL5 assistant: 0(1) lookup"


def test_digest_drops_command_wrappers(tmp_path: Path) -> None:
    lines = [
        {"type": "user", "message": {"content": "<command-name>/clear</command-name>"}},
        {"type": "user", "message": {"content": "real question"}},
    ]
    f = tmp_path / "s.jsonl"
    f.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    assert digest(f) == "L2 user: real question"


def test_clip_marks_what_was_cut() -> None:
    assert _clip("a" * 2000) == "a" * 2000
    assert _clip("a" * 2005).endswith("[...cut 5 chars]")


def test_digest_skips_malformed_lines(tmp_path: Path) -> None:
    f = tmp_path / "t.jsonl"
    f.write_text(
        '{"type": "user", "message": {"content": "hi"}}\n{"type": "user", "mess',
        encoding="utf-8",
    )
    assert digest(f) == "L1 user: hi"


def test_digest_drops_compaction_summary(tmp_path: Path) -> None:
    f = tmp_path / "t.jsonl"
    f.write_text(
        '{"type": "user", "isCompactSummary": true, "message": {"content": "summary"}}\n'
        '{"type": "user", "message": {"content": "why dict?"}}\n',
        encoding="utf-8",
    )
    assert digest(f) == "L2 user: why dict?"