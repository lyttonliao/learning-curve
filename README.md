# learning-curve

A Claude Code plugin that turns a project's development history into a course, so developers who build fast with AI still retain the concepts and tradeoffs. See `DESIGN.md` for the full design and `docs/phase-0-guide.md` for the build guide.

## Status: Phase 0 (decision log), steps 1–3 of 6

Phase 0 captures every real decision as an Architecture Decision Record (ADR) in `docs/decisions/`. Later phases (chapters, quizzes) read those ADRs.

| Step | Piece | State |
|---|---|---|
| 1 | `Decision` model, `validate` CLI, `schemas/decision.schema.json` | Done |
| 2 | ADR writer (`adr` CLI) | Done |
| 3 | `course` CLI (`init`, `session-end`, `queue`, `done`) | Code and tests done. `hooks/hooks.json` and a manual hook run are still to do |
| 4 | Transcript digest | Not started |
| 5 | Skills (`/learning-curve`, `/decision`) | Not started |
| 6 | Plugin manifest, live test | Not started |

## How it fits together

Three kinds of parts run in different ways:

| Part | Who runs it | Costs tokens? | Example |
|---|---|---|---|
| Hook | Claude Code, as a shell command on an event | No | copy a file when a session ends |
| Script | A hook, or Claude through the Bash tool | No | `validate`, `adr`, `course` |
| Skill | Claude, following written instructions | Yes | "find the decisions in this transcript" |

Rule: everything deterministic is a script. Only judgment (is this a real decision?) is left to the model.

### Data flow

```
session N ends
  └─ SessionEnd hook → course session-end      (no LLM)
       ├─ copy transcript → .course/transcripts/<session_id>.jsonl   (gitignored)
       └─ append          → .course/staged/queue.jsonl

session N+1: user runs /learning-curve          (skill, not built yet)
  ├─ course queue                  list pending sessions
  ├─ transcript digest             conversation text + line numbers   (Step 4)
  ├─ Claude proposes decisions, each citing transcript lines
  ├─ validate                      Pydantic check: the trust boundary
  ├─ user confirms / edits / rejects
  ├─ adr                           → docs/decisions/NNNN-slug.md
  └─ course done <ids>             drain the queue
```

Why a queue: extraction needs an LLM call, and running one from the hook would spend tokens on every session end. The hook only stages; extraction runs when the user chooses. The cost is a later review, with fainter memory.

Why copy the transcript: Claude Code deletes old transcripts (`cleanupPeriodDays`, default 30). A stored path would dangle.

Why the hook fails open: a crashing or hanging hook must never disturb session exit. A missed capture is cheaper. The cost is that failures are silent (stderr only).

## Modules

| Module | Role |
|---|---|
| `models.py` | `Decision`, `Option`, `Source`. Every field rule lives here |
| `validate.py` | CLI: validate a Decision JSON payload, or print its JSON Schema (`--schema`) |
| `adr.py` | CLI: write a validated Decision as `docs/decisions/NNNN-slug.md`. Never overwrites |
| `course.py` | CLI: `init`, `session-end`, `queue`, `done` for the `.course/` state |
| `cli.py` | Shared `fail` and `load_decision` helpers |

### `course`

| Subcommand | Does |
|---|---|
| `init` | Create `.course/transcripts/`, `.course/staged/`, and `.course/.gitignore` (`transcripts/`). Safe to re-run. This is the opt-in: `session-end` does nothing in a project without `.course/` |
| `session-end` | Read hook JSON (`session_id`, `transcript_path`, `cwd`) on stdin, copy the transcript, queue the session once. A resumed session re-copies the longer transcript but keeps one queue entry. Rejects a `session_id` that is not `[\w-]+` before writing, because it becomes a filename. Catches all errors, prints to stderr, exits 0 |
| `queue` | Print pending session ids, oldest first |
| `done <ids…>` | Remove ids from the queue. Unknown ids are ignored |

A session that is drained with `done` and later resumed is queued again, so it is extracted again. That is intended. The cost is possible duplicate proposals for decisions already confirmed.

## Usage

```bash
uv run pytest -q                                   # tests
uv run ruff check . && uv run ruff format --check . && uv run mypy learning_curve tests
```

The CLIs take a Decision JSON file or stdin:

```bash
PYTHONPATH=. uv run python -m learning_curve.validate decision.json
PYTHONPATH=. uv run python -m learning_curve.adr decision.json --root path/to/project
PYTHONPATH=. uv run python -m learning_curve.course --root path/to/project init
```

## Known issues

- **Packaging:** `pyproject.toml` has no `[build-system]`, so the package is not installed. `python -m learning_curve.<module>` fails with `ModuleNotFoundError` unless `PYTHONPATH` points at the repo root. `uv run --project <dir>` does not fix this. The hook command and the skills must set `PYTHONPATH="${CLAUDE_PLUGIN_ROOT}"`, or the project must gain a build system.
- **Hook runs are logged outside the project:** the `SessionEnd` command appends to `~/.learning-curve/hook.log`: a `[pid] started` line, all stderr, and a `[pid] finished exit=<code>` line. This captures failures before `main` runs (`ModuleNotFoundError`, `uv: command not found`). Reading the log: no `started` line means the hook never ran; `started` and `finished exit=0` with no error line means it ran and either queued the session or the project had not run `init`; `started` with no `finished` means it was killed (for example by the 10 s timeout).
  - Open: `$HOME` unwritable (the command never runs); one shared log with no rotation (about 2 short lines per session); the command's shell syntax (`$HOME`, `{ ...; }`) is verified only through `sh -c`, so confirm it in Step 6 under the real plugin loader.
- **Refs are format-checked only:** `Source.ref` is matched against a pattern. Nothing checks that the commit, PR or transcript line exists.
- **Queue rewrite is not atomic:** `done` rewrites `queue.jsonl` in place. A crash mid-write loses the queue. Acceptable while transcripts stay on disk.

## Next

1. `hooks/hooks.json` registering `SessionEnd`, with the `PYTHONPATH` prefix (Step 3).
2. Run the hook command by hand with fake stdin, from a different directory (Step 3 acceptance).
3. Transcript digest (Step 4), then the two skills (Step 5), then the plugin manifest and a live test (Step 6).
