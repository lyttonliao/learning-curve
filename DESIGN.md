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
| `importance` | `1`–`4`, computed in code from the extractor's rubric answers (see Importance rubric below), never graded by the LLM directly |
| `signals` | Cited learning signals, kept apart from importance: the dev stated something wrong and was corrected, a rejected alternative existed, it recurred. They feed quiz priority |
| `session_ids` | Sessions it came up in (a list: concepts recur) |
| `sources` | At least one; transcript refs must point into `session_ids` |
| `alternatives` | Optional |
| `misconception` | Optional: what the dev got wrong, and the correction. The strongest quiz seed |
| `tags` | Attach the note to a chapter section |

- **Importance** only picks which notes get quizzed when notes outnumber question slots. Structure comes from chapters and sections (§3). A "review all" mode lists every note in section order.

#### Importance rubric (decided 2026-11-27, from the step 2 spike)

Importance measures what the dev needs to know; signals measure where they were weak. Summing the two failed in the spike: `requires-python` scored high on signals alone, and the app's core technique (validated structured output, errors returned for retry) scored lowest because the dev never got it wrong.

The extractor answers three yes/no questions per note, each with a one-line reason written *before* the answer (JSON keys generate in order, so the model reasons first). Code applies them in order, first yes wins:

| Level | Question | Not knowing it means |
|---|---|---|
| 4 core | Is it what the app does, or why it is built this way? | You can't explain the app |
| 3 mechanism | Does the app's code depend on how this works? | You can't change or debug that code |
| 2 pitfall | Would not knowing it let a bug or bad pattern through review? | AI-written mistakes get past you |
| 1 context | None of the above | Nothing is blocked |

Level 3 is the supporting-technology layer that devs relying on AI tend to skip; level 2 is the review skill they need most.

- **Why yes/no answers, not a 1–4 grade:** LLM judges agree more on narrow binary checks than on scales, the reasons make each level auditable, and reordering levels or reweighting quiz priority is a code change with no new LLM call. Code-only rules can't tell core from mechanism; a separate grading call costs about 40% more tokens.
- **Accuracy levers in the prompt:** the app's purpose (§1–2, about 300 tokens; "core" is undefined without it), one real example per level from the spike, reason before answer, enum fields.
- **Quiz priority** = f(importance, signals), computed in code. Example: importance 2 with a misconception ranks above a plain 2.
- **Golden set:** the spike's 16 hand-rated notes (session `986bed3c`), confirmed by the dev:
  - 4: validate LLM output at a trust boundary and return errors as JSON
  - 3: cross-field model validators; nested `Source` over an encoded string; `after` vs `before` validators; `Annotated` aliases; model validator errors report at model level
  - 2: mypy checks annotations; `tmp_path`; regex dispatch table with `fullmatch`; one validator per rule; "required only when" has two directions; reference by name; field `date` shadows the type
  - 1: `uv.lock` vs `pyproject.toml`; `requires-python`; `.gitignore` hiding committed files

  Score the extractor by agreement with these levels; grade one session twice to measure drift. Add the separate grading call only if agreement is poor.
- **Attribution:** a correction counts as a signal only for whoever made the mistake. The assistant correcting itself is not "the dev was corrected", and "incomplete" is not "wrong".
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
2. **Extraction spike, by hand.** Done 2026-11-27 on session `986bed3c` (31,345-char digest): 17 notes, all valid against `Concept`. Findings:
   - **Citations:** a digest `L<n>` marks a whole message, up to about 60 lines. The first pass cited 18 refs that were well-formed but pointed at digest file lines, not entry markers, and the schema accepted all 18. Format checks are not enough.
   - **Count:** 17 notes from one mid-size session, so the placeholder cap of 15 is tight.
   - **`explanation`:** 186–473 chars; the 600 cap never bound. Keep it.
   - **`kind`:** 11 concept, 3 tradeoff, 3 debug. Plausible.
   - **Importance:** the summed-facts rubric conflated importance with weakness; replaced by the §4 Importance rubric.
   - **Duplicates:** "merge near-duplicates" is too vague. Rule: merge two notes only when one quiz question would test both (the `fullmatch` note merged into the regex dispatch note; three validator notes stay apart).
3. **Schema fixes from the spike.** Check each transcript `L<n>` is an entry marker in the digest; replace `importance` with the three rubric answers plus computed level, and add `signals`; the merge rule and rubric examples in the prompt; the `updates: <slug>` path for a recurring concept; a notes-per-session cap above 15.
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
17. **Notes per session.** What cap? 15 was already exceeded by one 31k-char session. The 600-char `explanation` held every spike note.
18. **Quiz selection.** When notes outnumber questions: the quiz priority function (§4) is decided in shape, not in weights. Is the rubric stable across runs? Measure against the golden set.
19. **Quiz config.** Question count, and pass thresholds per concept, chapter and quiz. Deferred until the note schema settles.
