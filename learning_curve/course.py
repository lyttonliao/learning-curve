"""`.course/` state: transcript copies and the queue of sessions awaiting extraction."""

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

_COURSE_DIR = ".course"
_SESSION_ID = re.compile(r"[\w-]+")


def init(root: Path) -> None:
    """Opt `root` in to capture. Transcripts are gitignored, since they may hold secrets.

    Safe to re-run.
    """
    course = root / _COURSE_DIR
    (course / "transcripts").mkdir(parents=True, exist_ok=True)
    (course / "staged").mkdir(exist_ok=True)
    (course / ".gitignore").write_text("transcripts/\n", encoding="utf-8")


def _queue_path(course: Path) -> Path:
    return course / "staged" / "queue.jsonl"


def _read_queue(queue: Path) -> list[dict[str, str]]:
    """Return queue entries in order; empty if there is no queue.

    Invalid lines are skipped, so one torn append cannot block every later call.
    """
    if not queue.is_file():
        return []
    entries = []
    with queue.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                # shortcut: that session stays unqueued, though its transcript is on disk;
                # upgrade to logging the line if sessions go missing.
                continue
    return entries


def _queued_ids(queue: Path) -> set[str]:
    return {e["session_id"] for e in _read_queue(queue)}


def pending(root: Path) -> list[str]:
    """Return the session ids awaiting extraction, oldest first."""
    return [e["session_id"] for e in _read_queue(_queue_path(root / _COURSE_DIR))]


def done(root: Path, ids: Sequence[str]) -> None:
    """Remove `ids` from the queue. Unknown ids are ignored."""
    queue = _queue_path(root / _COURSE_DIR)
    if not queue.is_file():
        return
    keep = [e for e in _read_queue(queue) if e["session_id"] not in ids]
    # shortcut: not atomic, so a crash mid-write loses the queue; acceptable while transcripts
    # stay on disk, upgrade to write-temp-then-rename if that changes.
    queue.write_text("".join(json.dumps(e) + "\n" for e in keep), encoding="utf-8")


def session_end(payload: dict[str, str]) -> None:
    """Copy the session's transcript and queue it once. No-op unless `cwd` ran `init`.

    A resumed session re-copies its longer transcript but keeps its single queue entry.

    Raises:
        ValueError: `session_id` is not safe to use as a filename.
    """
    course = Path(payload["cwd"]) / _COURSE_DIR
    if not course.is_dir():
        return
    session_id = payload["session_id"]
    if not _SESSION_ID.fullmatch(session_id):  # it becomes a filename: block "../x"
        raise ValueError(f"bad session_id {session_id!r}")
    shutil.copyfile(payload["transcript_path"], course / "transcripts" / f"{session_id}.jsonl")
    queue = _queue_path(course)
    if session_id in _queued_ids(queue):
        return
    entry = {"session_id": session_id, "ended_at": dt.datetime.now(dt.UTC).isoformat()}
    # Start a fresh line after a torn append, or this entry would be corrupted too.
    torn = queue.is_file() and queue.stat().st_size > 0 and not queue.read_bytes().endswith(b"\n")
    with queue.open("a", encoding="utf-8") as f:
        f.write(("\n" if torn else "") + json.dumps(entry) + "\n")


def main(argv: Sequence[str]) -> None:
    """Run one subcommand: `init`, `session-end`, `queue` or `done`.

    `session-end` never raises, so a broken hook cannot disturb session exit. Other failures
    raise and set the exit code.
    """
    parser = argparse.ArgumentParser(description="Manage the .course/ session queue.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="project root")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("session-end", help="SessionEnd hook; reads hook JSON on stdin")
    sub.add_parser("queue")
    sub.add_parser("done").add_argument("ids", nargs="+")
    args = parser.parse_args(argv)

    if args.command == "session-end":
        try:
            session_end(json.load(sys.stdin))
        except Exception as e:  # fail open: log and exit 0
            stamp = dt.datetime.now(dt.UTC).isoformat()
            print(
                f"{stamp} learning-curve: session-end failed: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
        return
    if args.command == "init":
        init(args.root)
    elif args.command == "queue":
        print("\n".join(pending(args.root)))
    else:
        done(args.root, args.ids)


if __name__ == "__main__":
    main(sys.argv[1:])
