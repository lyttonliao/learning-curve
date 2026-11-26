import io
import json
import re
from pathlib import Path

import pytest

from learning_curve.course import done, init, main, pending, session_end


def make_session(root: Path, session_id: str = "s1", text: str = "{}\n") -> dict[str, str]:
    """Write a fake transcript outside `root` and return the matching hook payload."""
    transcript = root.parent / f"{root.name}-src.jsonl"
    transcript.write_text(text, encoding="utf-8")
    return {"session_id": session_id, "transcript_path": str(transcript), "cwd": str(root)}


def queue_lines(root: Path) -> list[dict[str, str]]:
    text = (root / ".course" / "staged" / "queue.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


def test_init_creates_dirs_and_gitignore_and_is_rerunnable(tmp_path: Path) -> None:
    init(tmp_path)
    init(tmp_path)
    assert (tmp_path / ".course" / "transcripts").is_dir()
    assert (tmp_path / ".course" / "staged").is_dir()
    assert (tmp_path / ".course" / ".gitignore").read_text() == "transcripts/\n"


def test_session_end_copies_transcript_and_queues(tmp_path: Path) -> None:
    init(tmp_path)
    session_end(make_session(tmp_path, "s1", "line\n"))
    copy = tmp_path / ".course" / "transcripts" / "s1.jsonl"
    assert copy.read_text() == "line\n"
    [entry] = queue_lines(tmp_path)
    assert entry["session_id"] == "s1"
    assert entry["ended_at"]


def test_resumed_session_recopies_but_keeps_one_queue_entry(tmp_path: Path) -> None:
    init(tmp_path)
    session_end(make_session(tmp_path, "s1", "short\n"))
    session_end(make_session(tmp_path, "s1", "short\nlonger\n"))
    copy = tmp_path / ".course" / "transcripts" / "s1.jsonl"
    assert copy.read_text() == "short\nlonger\n"
    assert len(queue_lines(tmp_path)) == 1


def test_opted_out_project_is_untouched(tmp_path: Path) -> None:
    session_end(make_session(tmp_path))
    assert not (tmp_path / ".course").exists()


@pytest.mark.parametrize("session_id", ["../evil", "a/b", "", "a b"])
def test_bad_session_id_is_rejected_before_any_write(tmp_path: Path, session_id: str) -> None:
    init(tmp_path)
    payload = make_session(tmp_path, session_id)
    with pytest.raises(ValueError, match="bad session_id"):
        session_end(payload)
    assert list((tmp_path / ".course" / "transcripts").iterdir()) == []


def test_pending_lists_in_order_and_is_empty_without_a_queue(tmp_path: Path) -> None:
    init(tmp_path)
    assert pending(tmp_path) == []
    for sid in ("b", "a", "c"):
        session_end(make_session(tmp_path, sid))
    assert pending(tmp_path) == ["b", "a", "c"]


def test_done_removes_only_the_given_ids(tmp_path: Path) -> None:
    init(tmp_path)
    for sid in ("a", "b", "c"):
        session_end(make_session(tmp_path, sid))
    done(tmp_path, ["a", "c", "unknown"])
    assert pending(tmp_path) == ["b"]


def test_done_on_a_missing_queue_does_not_crash(tmp_path: Path) -> None:
    init(tmp_path)
    done(tmp_path, ["a"])
    assert pending(tmp_path) == []


def test_done_without_init_does_not_crash(tmp_path: Path) -> None:
    done(tmp_path, ["a"])
    assert not (tmp_path / ".course").exists()


def test_corrupt_queue_line_is_skipped(tmp_path: Path) -> None:
    init(tmp_path)
    session_end(make_session(tmp_path, "a"))
    queue = tmp_path / ".course" / "staged" / "queue.jsonl"
    with queue.open("a", encoding="utf-8") as f:
        f.write('{"session_id": "b", "ended')  # half-written append
    session_end(make_session(tmp_path, "c"))
    assert pending(tmp_path) == ["a", "c"]


def test_main_session_end_reads_stdin_and_queues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init(tmp_path)
    payload = make_session(tmp_path, "s1")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    main(["session-end"])
    assert pending(tmp_path) == ["s1"]


def test_main_session_end_fails_open_on_missing_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    init(tmp_path)
    payload = {"session_id": "s1", "transcript_path": str(tmp_path / "nope"), "cwd": str(tmp_path)}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    main(["session-end"])  # must not raise
    err = capsys.readouterr().err
    # ISO timestamp, then the exception type, so the log line is self-explanatory.
    assert re.match(r"\d{4}-\d\d-\d\dT.* session-end failed: FileNotFoundError:", err)
    assert pending(tmp_path) == []


def test_main_session_end_fails_open_on_garbage_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    main(["session-end"])
    assert "session-end failed" in capsys.readouterr().err


def test_main_init_queue_done_round_trip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["--root", str(tmp_path), "init"])
    session_end(make_session(tmp_path, "s1"))
    main(["--root", str(tmp_path), "queue"])
    assert capsys.readouterr().out == "s1\n"
    main(["--root", str(tmp_path), "done", "s1"])
    assert pending(tmp_path) == []
