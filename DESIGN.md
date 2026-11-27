# learning-curve — Design

A Claude Code skill that turns a project's development history into a course, so developers who build fast with AI still retain concepts, tradeoffs and fundamentals.

## 1. Why

- AI use erodes learning. Anthropic skill-formation study (Jan 2026, arXiv 2601.20245): full delegation to AI is fastest but yields the least learning; asking conceptual questions preserves it.
- METR randomized controlled trial (RCT): experienced devs were 19% slower with AI but felt 20% faster.
- GitClear: code churn and duplication up, refactoring down.
- Closest existing tool: codebase-to-course (repo snapshot → course).
- **Differentiator:** learning-curve teaches *how the code got here*: the concepts, tradeoffs and decisions (with their rejected alternatives) met along the way, not a snapshot.

## 2. Product

| | |
|---|---|
| Audience | Any solo developer who builds fast but wants retention |
| Scope | Solo only. No team features. |
| Form factor | Claude Code skill that writes a static course. Markdown first, HTML site later. Packaged as a Claude Code plugin, because a bare skill cannot ship hooks. |
| Lifecycle | Backfill from past git history, then grow iteratively. Chapters written as code is written, or when prompted. |
| Activation | Skill should be active from project start, to build context. |
| Dogfooding | Build learning-curve with learning-curve. |

## 3. Course structure

### Chapters
- **Chapter** = a full feature (new user-facing capability or subsystem) **AND** at least one ambiguous decision (alternatives weighed in conversation, or multiple agents disagreed).
- **Section** = one topic within a chapter. The LLM splits work into chapters, and each chapter into sections by topic.
- **Fixes/enhancements** don't warrant a quiz, unless the change is important.
- Large diff alone is a weak signal. It must be backed by conversation/decisions.
- **Revisited decisions:** a refactor that reverses an earlier decision links as `revisited` on the original decision and feeds the next quiz. Rationale: the first solution is often a quick proof of concept (POC); don't add complexity before value is verified.

### Section content
- Teach the fundamentals under the code. Example chain: `SELECT ... FOR UPDATE` → row locks → deadlocks → isolation levels.
- **Debug drills:** given a symptom, where do you look? Goal: never forget how to code and debug.

## 4. Decisions and concept notes

Two kinds of record. Both are validated before anything is written, and both cite their sources. Both directories are committed.

- **Decisions** are Architecture Decision Records (ADRs) at `docs/decisions/NNNN-slug.md`.
- **Concept notes** capture what was learned along the way: concepts, tradeoffs and debug lessons, at `docs/concepts/<slug>.md`. Quizzes and prose are generated from notes and ADRs, never from raw transcripts.

### Decisions (ADRs)

| Field | Values / meaning |
|---|---|
| `status` | `provisional` \| `accepted` \| `superseded-by-NNNN` |
| `context` | Problem and constraints |
| `options_considered` | Alternatives weighed |
| `chosen` | The option taken |
| `tradeoffs` | What was given up |
| `upgrade_trigger` | When the provisional choice stops being good enough |
| `source` | transcript ref \| PR \| `inferred` |

- Decisions backfilled from history are marked `source: inferred`.
- Every decision cites a source (SHA / PR / transcript line) to limit hallucination.
- Candidate: a manual `/decision` command for decisions made outside transcripts.

### Concept notes

| Field | Values / meaning |
|---|---|
| `title`, `kind` | `concept` \| `tradeoff` \| `debug` |
| `explanation` | Just enough detail to write a quiz from (max 600 chars, to tune) |
| `why_it_came_up` | The situation that surfaced it |
| `importance` | `1` \| `2` \| `3`, assigned by the extractor against a rubric of checkable facts: the dev was corrected, a rejected alternative existed, it touches several files, it recurred |
| `session_ids` | Sessions it came up in (a list: concepts recur) |
| `sources` | At least one; transcript refs must point into `session_ids` |
| `alternatives` | Optional |
| `misconception` | Optional: what the dev got wrong, and the correction. The strongest quiz seed |
| `tags` | Attach the note to a chapter section |

- **Importance** only picks which notes get quizzed when notes outnumber question slots. Structure comes from chapters and sections (§3). A "review all" mode lists every note in section order.
- **Idempotency:** per session through the queue (`course done`). Per note, the writer never overwrites a slug. A concept seen again should update its note (`updates: <slug>`), not add one; not built yet.

## 5. Quizzes

- **When:** end of each feature chapter.
- **Format:** open-ended. Covers key concepts, the tradeoffs, reaffirming project decisions, "what breaks if we switched to Y", "what would trigger replacing this".
- **Principle:** if the dev can't answer, they shouldn't continue — tech debt grows where understanding is missing.
- **Grading:** judged against the concept notes and ADRs + a rubric. Rubric shown *after* answering. Grading runs in a separate headless call (`claude -p` with a fixed rubric), not in the chat.

### Difficulty (config)

| Mode | Behavior |
|---|---|
| `learn` | Quiz offered, no consequence |
| `standard` | Quiz required. Fail → gap report; may continue. |
| `strict` | Must pass (e.g. ≥80%). Fail = hard stop, enforced by a `PreToolUse` hook on `Edit\|Write` reading `.course/state.json`. |

### Frequency (config)
- Every feature chapter (default), every N chapters, or on demand.
- Minimum chapter size.

## 6. Retest design

1. **Grade per concept.** Rubric items map to concept ids.
2. **Gap report** says what was missing — fundamental / tradeoff / rationale — with code lines and ADR links.
3. **Targeted remediation:** a section for failed concepts only.
4. **Retest** only failed concepts, with fresh questions from a new angle (no memorizing).
5. **Spaced review** of passed concepts at 1 / 3 / 7 / 21 days; shorter intervals after a failure.
6. **Escape hatch** (even in strict): after N failures or an explicit override, continue but log `knowledge-debt: <concepts>`, which resurfaces in the next quiz.

The gate is a commitment device for a solo dev, not anti-cheat. The user controls the session and the state.

## 7. Stack

No backend. The user's own Claude session is the model.

### Ships
| Piece | Role |
|---|---|
| `SKILL.md` | Prompts: chapter detection, decision and concept extraction, section authoring, question generation, grading rubric |
| `schemas/` + `validate.py` | JSON schemas + Pydantic validation (`Decision`, `Concept`) of Claude output before writing state |
| `SessionEnd` hook | Copies the transcript and queues the session; no LLM call |
| `PreToolUse` hook | Strict-mode gate |
| Headless grader | `claude -p` with fixed rubric |
| State | `.course/config.yaml`, `.course/state.json`, `.course/chapters/`, `docs/decisions/`, `docs/concepts/` |
| Scheduler | Fixed intervals in plain Python. Swap to the `fsrs` library only if needed. |
| Retrieval | None. Filter notes by session, tag or chapter, and use Claude Code's Grep/Read. Add search only when notes outgrow one request. |

### Dev-only (author)
- pytest eval harness:
  - ~50 hand-labeled commit groups → chapter-detector precision/recall.
  - ~30 hand-graded answers → grader agreement (Cohen's kappa). Below ~0.6 means the strict gate is not trustworthy.
- Evals run in GitHub Actions on prompt changes.

### Author learning goals
Prompt engineering, structured outputs, context engineering, LLM-as-judge, evals, Claude Code hooks and headless mode.

## 8. Dropped for now

Future hosted-tier project: embeddings / vector DB, fine-tuning / distillation, XGBoost recall model, MCP server, Prometheus metrics, hosted tier.

Note: local retrieval could ship inside a skill. Only fine-tuning and shared indexes need hosting.

## 9. Risks

| Risk | Mitigation (as decided) |
|---|---|
| Hallucinated decisions | Cite sources: SHA / PR / transcript line |
| Token cost on user's plan | Prompt efficiency is a feature |
| Grading too lenient / strict | Grader-agreement eval (kappa ≥ ~0.6 before trusting strict) |
| Decisions made outside transcripts are lost | Candidate `/decision` command |
| Transcripts expire before capture (`cleanupPeriodDays`, default 30) | `course init` + the `SessionEnd` hook, active from project start |

## 10. Roadmap (proposed)

Status: proposed, not yet accepted. Ordering principle: each phase is usable on its own, and dogfooding starts in Phase 0.

### Phase 0 — Decision log and concept notes
**Goal:** capture decisions and concepts from day one. The skill must be active from project start, and decisions are the input every later phase consumes.

In scope:
- Plugin layout: `.claude-plugin/plugin.json`, `skills/learning-curve/SKILL.md`, `skills/decision/SKILL.md`, `hooks/hooks.json`, `learning_curve/` (Python package), `schemas/`, `tests/`, `pyproject.toml`. Scripts run via `uv run --project ${CLAUDE_PLUGIN_ROOT}`, so `uv` is a user requirement.
- Pydantic `Decision` model + exported JSON schema, matching the §4 fields.
- `learning_curve.validate`: validates Claude's JSON output before anything is written.
- `learning_curve.transcript`: digest of a transcript — conversation text only, keyed by JSONL line for citations. Measured: 1,951,074 → 65,627 chars (about 16k tokens). Each entry has an 8,000-char head+tail guard; no real entry in 4 sessions exceeded it.
- Pydantic `Concept` model and note writer: validated concept → `docs/concepts/<slug>.md`, never overwriting.
- ADR writer: validated decision → `docs/decisions/NNNN-slug.md` (next free number, slugified title).
- `SessionEnd` hook: preserves context, spends no tokens. It copies the transcript to `.course/transcripts/<session_id>.jsonl` and appends `{session_id, ended_at}` to `.course/staged/queue.jsonl`.
  - The copy matters because deferred extraction must not lose context: Claude Code deletes old transcripts (`cleanupPeriodDays`, default 30).
  - `.course/transcripts/` is gitignored: transcripts may contain secrets.
- Deferred extraction (`SKILL.md`): the queue is drained in-session, the next time the skill runs or before any chapter is generated, whichever comes first. Claude extracts candidate decisions and concept notes with transcript line refs, `validate.py` checks them, and the user confirms/edits/rejects. Only confirmed ones are written as ADRs.
- `/decision` command: manual entry for decisions made outside transcripts.
- pytest: model validation (good + bad payloads), ADR numbering/rendering, hook copy + queue append, digest.

Tradeoff: defer extraction rather than run `claude -p` in the hook. No hidden token spend at every session end, and several sessions can be extracted in one pass. Cost: candidates aren't ready until the next run, and the user confirms them with a less fresh memory. Upgrade trigger: confirmations become unreliable because too much time passes between session and review.

Out of scope: chapters, backfill, quizzes, grader, gate, scheduler, evals, `.course/config.yaml`, `.course/state.json`.

**Exit criteria:** learning-curve's own design decisions exist as ADRs in `docs/decisions/`, and concept notes from its own sessions exist in `docs/concepts/`, written through the skill (staged flow and `/decision` each used at least once).

#### Revised plan (2026-11-26)

Built: `Decision` + `validate`, ADR writer, `course` queue + `SessionEnd` hook config, transcript digest, `Concept` model + note writer. Order from here:

1. **Start capturing.** Done 2026-11-27: `course init` run here, `SessionEnd` hook registered in `.claude/settings.local.json` (via `$CLAUDE_PROJECT_DIR`, since the plugin is not installed; remove at step 6), and the 6 existing transcripts backfilled. Backfill only reaches sessions inside `cleanupPeriodDays` (default 30); a `course backfill` subcommand is a candidate for step 4 or 6.
2. **Extraction spike, by hand.** Prompt + one real digest → `list[Concept]` → validate → judge the notes. Tests the schema (600-char cap, `importance`, `kind`s, notes per session) before more is built on it.
3. **Schema fixes from the spike.** Check each transcript `L<n>` exists in the digest; the `updates: <slug>` path for a recurring concept; a notes-per-session cap.
4. **Notes CLI** taking a list of concepts (generic payload loader shared with `validate` and `adr`).
5. **Skills** (guide Step 5), rewritten to extract both kinds.
6. **Plugin manifest + live test** (guide Step 6).
7. **ADR 0001** "From decision log to concept notes", written through the pipeline.

Deferred: chunking the digest. The largest measured digest is 65,627 chars, which fits one pass. Split at exchange boundaries (a user prompt plus its responses), repeating one exchange across the cut, only when a digest passes about 100,000 chars.

### Later phases
| Phase | Scope | Eval gate |
|---|---|---|
| 1 — Chapters | Chapter detection, section authoring (fundamentals, debug drills), git-history backfill with `inferred` ADRs, `revisited` links | Chapter-detector precision/recall on ~50 labeled commit groups; evals in GitHub Actions from here on |
| 2 — Quizzes (`learn`) | Question generation, headless grader via `claude -p`, per-concept rubric, rubric shown after answering | Grader agreement on ~30 hand-graded answers (Cohen's kappa) |
| 3 — Enforcement | `standard` + `strict`, `PreToolUse` gate, gap report, targeted remediation, retest, escape hatch / `knowledge-debt` | Strict ships only if kappa ≥ ~0.6 |
| 4 — Spaced review | 1/3/7/21-day scheduler, frequency config | — |
| 5 — HTML site | Static site from the Markdown course | — |

## 11. Open questions

Gaps noticed while writing this. Not decided.

1. **Phases.** Proposed in §10. Accept or revise?
2. **Pass threshold for `standard`.** Strict uses e.g. ≥80%; does standard use a threshold to trigger the gap report?
3. **Escape-hatch N.** How many failures before the hatch opens? Configurable?
4. **Minimum chapter size.** Measured in what — sections, commits, lines, decisions?
5. **"Shorter after failure" intervals.** Exact schedule?
6. **ADR status transitions.** Who/what moves `provisional` → `accepted`? Who sets `upgrade_trigger` for inferred ADRs?
7. **Agent disagreement signal.** How is "multiple agents disagreed" detected from transcripts?
8. **Backfill scope.** How far back in git history, and what token budget for a first run on a large repo?
9. **SessionEnd staging.** Decided in §10: hook copies transcript + queues it; extraction deferred. Size: 8,000-char per-entry guard; chunk past about 100,000 chars per digest (see the revised plan).
10. **Quiz records.** Where are answers, grades and concept states stored — all in `.course/state.json`?
11. **`/decision` command.** Proposed in §10: in, Phase 0.
12. **HTML site.** What triggers moving from Markdown to HTML?
13. **"Important" fixes/enhancements.** What makes a fix or enhancement important enough for a quiz? Where in the course does a fix/enhancement go — into the matching topic section of its chapter?
14. **Draining trigger.** Nothing prompts the user to run the review, so the queue can sit unread. Candidate: a `SessionStart` hook that prints one line ("N sessions staged — run /learning-curve") when the queue is non-empty.
15. **`/decision` citations.** Manual decisions can cite only the whole session (`<session_id>:L1`), not the exact line. `${CLAUDE_SESSION_ID}` substitution in skills is unverified.
16. **Concept merging.** How does the extractor match a new concept to an existing note: by title, by tags, or by showing it the list of note titles?
17. **Notes per session.** What cap (15 is a placeholder), and is the 600-char `explanation` enough to write a quiz from?
18. **Quiz selection.** When notes outnumber questions: by `importance`, then recency? Is the 1–3 rubric stable across runs?
19. **Quiz config.** Question count, and pass thresholds per concept, chapter and quiz. Deferred until the note schema settles.
