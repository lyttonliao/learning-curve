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
        {"type": "text", "text": "b"},
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


def test_clip_keeps_head_and_tail() -> None:
    assert _clip("a" * 8000) == "a" * 8000
    text = "h" * 4000 + "m" * 5 + "t" * 4000
    assert _clip(text) == "h" * 4000 + " [...cut 5 chars...] " + "t" * 4000


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


def test_digest_strips_inline_reminders(tmp_path: Path) -> None:
    f = tmp_path / "t.jsonl"
    f.write_text(
        '{"type": "user", "message": {"content": '
        '"why dict?\\n<system-reminder>\\nnoise\\n</system-reminder>"}}\n'
        '{"type": "user", "message": {"content": '
        '"<system-reminder>only noise</system-reminder>"}}\n',
        encoding="utf-8",
    )
    assert digest(f) == "L1 user: why dict?"


def test_digest_every_entry_type(tmp_path: Path) -> None:
    entries = [
        {"type": "attachment"},
        {"type": "user", "message": {"content": "why dict?"}},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "thinking", "thinking": "hmm"},
                    {"type": "text", "text": "O(1) lookup"},
                    {"type": "tool_use", "name": "Read", "input": {}},
                ]
            },
        },
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]}},
        {"type": "user", "isMeta": True, "message": {"content": "meta"}},
        {"type": "user", "isCompactSummary": True, "message": {"content": "summary"}},
        {"type": "user", "message": {"content": "<command-name>/clear</command-name>"}},
    ]
    last = {"type": "assistant", "message": {"content": "ok<system-reminder>x</system-reminder>"}}
    raw = [json.dumps(e) for e in entries] + ["{not json", "", json.dumps(last)]
    f = tmp_path / "t.jsonl"
    f.write_text("\n".join(raw), encoding="utf-8")
    assert digest(f) == "L2 user: why dict?\n\nL3 assistant: O(1) lookup\n\nL10 assistant: ok"
