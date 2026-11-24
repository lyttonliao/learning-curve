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
    """Create `.course/` dirs and gitignore transcripts. Safe to re-run."""
    course = root / _COURSE_DIR
    (course / "transcripts").mkdir(parents=True, exist_ok=True)
    (course / "staged").mkdir(exist_ok=True)
    (course / ".gitignore").write_text("transcripts/\n", encoding="utf-8")


def _read_queue(queue: Path) -> list[dict[str, str]]:
    """Return queue entries in order; empty if the file doesn't exist yet."""
    if not queue.is_file():
        return []
    with queue.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _queue_path(course: Path) -> Path:
    return course / "staged" / "queue.jsonl"


def _queued_ids(queue: Path) -> set[str]:
    """Return the session ids already in `queue`."""
    return {e["session_id"] for e in _read_queue(queue)}


def pending(root: Path) -> list[str]:
    """Session ids waiting for extraction, oldest first."""
    return [e["session_id"] for e in _read_queue(_queue_path(root / _COURSE_DIR))]


def done(root: Path, ids: Sequence[str]) -> None:
    """Remove `ids` from the queue. Unknown ids are ignored."""
    queue = _queue_path(root / _COURSE_DIR)
    keep = [e for e in _read_queue(queue) if e["session_id"] not in ids]
    # shortcut: rewrite is not atomic, a crash mid-write loses the queue; fine while
    # transcripts stay on disk, upgrade to write-temp-then-rename if that changes.
    queue.write_text("".join(json.dumps(e) + "\n" for e in keep), encoding="utf-8")


def session_end(payload: dict[str, str]) -> None:
    """Copy the transcript and queue the session. No-op unless `init` ran in `cwd`."""
    course = Path(payload["cwd"]) / _COURSE_DIR
    if not course.is_dir():
        return  # opt-in: projects that never ran init stay untouched
    session_id = payload["session_id"]
    # session_id becomes a filename: reject "../x" before it reaches the filesystem.
    if not _SESSION_ID.fullmatch(session_id):
        raise ValueError(f"bad session_id {session_id!r}")
    shutil.copyfile(payload["transcript_path"], course / "transcripts" / f"{session_id}.jsonl")
    queue = _queue_path(course)
    if session_id in _queued_ids(queue):
        return  # resumed session: transcript re-copied above, keep one entry
    entry = {"session_id": session_id, "ended_at": dt.datetime.now(dt.UTC).isoformat()}
    with queue.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def main(argv: Sequence[str]) -> None:
    """Run one subcommand (init, session-end, queue, done).

    Returns nothing: every failure is either swallowed on purpose (session-end, fail open)
    or raised, so the process exit code comes from the exception or from argparse.
    """
    parser = argparse.ArgumentParser(description="Manage the .course/session queue.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="project root")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("session-end", help="SessionEnd hook; reads hook JSON on stdin")
    sub.add_parser("queue")
    sub.add_parser("done").add_argument("ids", nargs="+")
    args = parser.parse_args(argv)

    if args.command == "session-end":
        # Fail open: a broken hook must never block or break session exit.
        try:
            session_end(json.load(sys.stdin))
        except Exception as e:  # deliberate catch-all: see the fail-open comment above
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
