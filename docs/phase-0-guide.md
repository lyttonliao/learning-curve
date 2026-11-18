# Phase 0 build guide — you write the code

You build Phase 0 (the decision log) yourself. This guide gives you: what we are building and how a Claude Code plugin works (§1), a learning path to master each technology (§2), six build steps with specs and acceptance criteria (§3), and how every design choice was derived (§4).

No reference implementation exists. Claude reviews your code against the acceptance criteria; it does not write it.

All links were checked on 2026-11-18.

---

## 0. How to work each step

1. Read the step's docs. Answer its **pre-check** questions (in chat, before coding).
2. Write the code and tests.
3. Run the gate (set up in Step 1):
   ```bash
   uv run ruff check . && uv run ruff format --check . && uv run mypy learning_curve && uv run pytest -q
   ```
4. Ask Claude to review. Fix findings.
5. Commit (one commit per step, Conventional Commits style: https://www.conventionalcommits.org/en/v1.0.0/).
6. Answer the step's **mastery check** questions. Claude grades them and logs them to `~/claude-learning-log.md`.

Start from `main`:
```bash
cd ~/work/learning-curve && git switch -c phase-0/mine
```

---

## 1. What we are building

### 1.1 The goal of Phase 0
Capture every real decision from day one, as an Architecture Decision Record (ADR) in `docs/decisions/`. Later phases (chapters, quizzes, retests) read these ADRs. If decisions are not captured while they happen, they are lost.

### 1.2 How Claude Code runs a plugin
A plugin is a folder that Claude Code loads. It bundles three kinds of parts that run in very different ways:

| Part | Who runs it | When | Costs tokens? |
|---|---|---|---|
| **Skill** (`skills/<name>/SKILL.md`) | Claude, following the instructions | When the user types `/<name>`, or Claude decides the skill's `description` matches the task | Yes. Only the `description` sits in context until the skill is used; the body loads on use ("progressive disclosure"). |
| **Hook** (`hooks/hooks.json`) | Claude Code itself, as a shell command | On a lifecycle event (`SessionEnd`, `PreToolUse`, …). Event data arrives as JavaScript Object Notation (JSON) on stdin. | No. It is a plain program. |
| **Scripts** (our Python package) | Claude (through the Bash tool) or a hook | When a skill tells Claude to run them, or a hook calls them | No. Deterministic code. |

Design rule that follows: **put everything deterministic in Python scripts, and keep only judgment in the skill prompt.** Validation, numbering, file writes and copying are code. Deciding "is this a real decision?" is the Large Language Model (LLM).

### 1.3 Data flow

```
 session N (any Claude Code session in a project that ran `init`)
   │
   └─ ends ──► SessionEnd hook (Python, no LLM)
                 ├─ copy transcript ──► .course/transcripts/<id>.jsonl   (gitignored)
                 └─ append entry   ──► .course/staged/queue.jsonl

 session N+1: user runs /learning-curve
   │
   ├─ skill: list queue                          (script)
   ├─ skill: digest transcript to text + line numbers   (script)
   ├─ Claude: extract candidate decisions with citations  (LLM judgment)
   ├─ skill: validate each candidate JSON        (script, Pydantic)
   ├─ user: confirm / edit / reject              (human in the loop)
   ├─ skill: write ADR  ──► docs/decisions/NNNN-slug.md   (script)
   └─ skill: mark session done in queue          (script)

 any time: /learning-curve:decision  ──► manual ADR (same validate + write path)
```

### 1.4 Target layout

```
.claude-plugin/plugin.json        plugin manifest
hooks/hooks.json                  SessionEnd → python -m learning_curve.course session-end
skills/learning-curve/SKILL.md    init + review flow
skills/decision/SKILL.md          manual entry
learning_curve/                   Python package
  models.py                       Pydantic models (Decision, Option, Source)
  validate.py                     CLI: validate JSON against a model; print JSON Schema
  adr.py                          CLI: validated Decision → docs/decisions/NNNN-slug.md
  course.py                       CLI: init, queue, done, session-end
  transcript.py                   CLI: transcript digest
schemas/decision.schema.json      generated from models.py; committed
tests/                            pytest
pyproject.toml                    uv project, deps, ruff/mypy/pytest config
```

Scripts are run as `uv run -q --project "${CLAUDE_PLUGIN_ROOT}" python -m learning_curve.<module>`, so they work from any project directory. `${CLAUDE_PLUGIN_ROOT}` is filled in by Claude Code with the plugin's install path.

---

## 2. Learning path

Each block: what to master, where to learn it, and a self-check. Do the **Foundations** before Step 1; do the rest just before the step that needs it.

### 2.1 Foundations (before Step 1)

**Why this project exists** (read once, 30 min):
- Anthropic skill-formation study: https://arxiv.org/abs/2601.20245
- METR (Model Evaluation and Threat Research) study of experienced developers with AI: https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/

**Claude Code mental model:**
- Overview: https://code.claude.com/docs/en/overview
- Best practices (Anthropic engineering): https://www.anthropic.com/engineering/claude-code-best-practices
- Memory and CLAUDE.md: https://code.claude.com/docs/en/memory
- Self-check: what is the difference between CLAUDE.md, a skill, and a hook? Which ones does the model read, and which ones run without it?

**Python tooling (uv, ruff, mypy):**
- uv getting started: https://docs.astral.sh/uv/getting-started/
- uv projects guide: https://docs.astral.sh/uv/guides/projects/
- uv project layout and lockfile: https://docs.astral.sh/uv/concepts/projects/layout/
- uv dependencies and dependency groups: https://docs.astral.sh/uv/concepts/projects/dependencies/
- Writing `pyproject.toml`: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- Ruff (linter + formatter): https://docs.astral.sh/ruff/
- Self-check: what does `uv.lock` guarantee that `pyproject.toml` does not? What does `uv run` do before running your command?

**Python typing + mypy:**
- `typing` module: https://docs.python.org/3/library/typing.html
- mypy cheat sheet: https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html
- mypy command line (`--strict`): https://mypy.readthedocs.io/en/stable/command_line.html
- Self-check: list three checks `--strict` turns on. What does `Self` express that returning the class name does not?

**pytest:**
- Getting started: https://docs.pytest.org/en/stable/getting-started.html
- Good practices (layout, imports): https://docs.pytest.org/en/stable/explanation/goodpractices.html
- Fixtures: https://docs.pytest.org/en/stable/how-to/fixtures.html
- Self-check: what does a fixture give you over a helper function? When would you use `tmp_path` vs a fixture of your own?

### 2.2 Pydantic and structured output (Step 1)
- Why Pydantic: https://docs.pydantic.dev/latest/why/
- Models: https://docs.pydantic.dev/latest/concepts/models/
- Fields and constraints: https://docs.pydantic.dev/latest/concepts/fields/
- Types (dates, literals, constrained strings): https://docs.pydantic.dev/latest/concepts/types/
- Config (`extra`, string stripping): https://docs.pydantic.dev/latest/concepts/config/
- Validators: https://docs.pydantic.dev/latest/concepts/validators/
- JSON Schema generation: https://docs.pydantic.dev/latest/concepts/json_schema/
- Validation errors: https://docs.pydantic.dev/latest/errors/validation_errors/
- mypy plugin: https://docs.pydantic.dev/latest/integrations/mypy/
- JSON Schema from first principles: https://json-schema.org/learn/getting-started-step-by-step
- LLM side — structured outputs: https://docs.claude.com/en/docs/build-with-claude/structured-outputs
- Self-check: what is the difference between a "before" and an "after" model validator? Why do we validate Claude's JSON even when we ask it to follow a schema?

### 2.3 Files, regex, CLIs (Steps 2–4)
- `pathlib`: https://docs.python.org/3/library/pathlib.html
- `open()` and its modes: https://docs.python.org/3/library/functions.html
- `json`: https://docs.python.org/3/library/json.html
- Regular expressions how-to: https://docs.python.org/3/howto/regex.html
- `re` reference: https://docs.python.org/3/library/re.html
- `shutil`: https://docs.python.org/3/library/shutil.html
- Structural pattern matching tutorial (Python Enhancement Proposal (PEP) 636): https://peps.python.org/pep-0636/
- JSON Lines: https://jsonlines.org/
- YAML 1.2 spec (how it relates to JSON): https://yaml.org/spec/1.2.2/
- Git revision syntax (SHA forms): https://git-scm.com/docs/gitrevisions
- pytest `tmp_path`: https://docs.pytest.org/en/stable/how-to/tmp_path.html
- pytest `monkeypatch`: https://docs.pytest.org/en/stable/how-to/monkeypatch.html
- pytest `capsys`: https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html
- Self-check: what is the difference between `re.match`, `re.search` and `re.fullmatch`? Which one belongs in a validator, and why?

### 2.4 ADRs (Step 2)
- ADR overview: https://adr.github.io/
- Michael Nygard's original post: https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- Self-check: why are ADRs append-only (superseded, not edited)?

### 2.5 Claude Code hooks, skills, plugins (Steps 3, 5, 6)
- Hooks guide (tutorial): https://code.claude.com/docs/en/hooks-guide
- Hooks reference (events, stdin schema, exit codes): https://code.claude.com/docs/en/hooks
- Settings (incl. transcript cleanup): https://code.claude.com/docs/en/settings
- Skills in Claude Code: https://code.claude.com/docs/en/skills
- Agent Skills overview: https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview
- Agent Skills best practices: https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices
- Engineering post on skills: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- Plugins: https://code.claude.com/docs/en/plugins
- Plugins reference (manifest, layout, variables): https://code.claude.com/docs/en/plugins-reference
- Plugin marketplaces (distribution, later): https://code.claude.com/docs/en/plugin-marketplaces
- CLI reference (`--plugin-dir`, `-p`): https://code.claude.com/docs/en/cli-reference
- Offline examples on your machine: `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/` (see `plugin-dev/skills/hook-development/SKILL.md` and `plugin-dev/skills/plugin-structure/SKILL.md`)
- Self-check: what happens to the user's session if a `SessionEnd` hook exits non-zero or hangs? How does a skill's `description` decide when it triggers?

### 2.6 Prompt and context engineering (Steps 4–5)
- Prompt engineering overview: https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview
- Effective context engineering for agents: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Self-check: the review flow reads a digest, not the raw transcript. Name two benefits and one risk.

### 2.7 Preview for later phases (not needed for Phase 0)
- Headless mode (`claude -p`, the Phase 2 grader): https://code.claude.com/docs/en/headless
- Subagents: https://code.claude.com/docs/en/sub-agents
- Building evaluations: https://docs.claude.com/en/docs/test-and-evaluate/develop-tests
- Cohen's kappa (grader agreement): https://en.wikipedia.org/wiki/Cohen%27s_kappa
- Prompt caching (token cost): https://docs.claude.com/en/docs/build-with-claude/prompt-caching
- Optional book on Python architecture, free online: https://www.cosmicpython.com/book/preface.html

---

## 3. Build steps

Each step pairs one engineering concept with one LLM-tooling concept.

### Step 1 — Project setup + `Decision` model
**Goal:** a uv project with ruff, mypy (strict, Pydantic plugin) and pytest, plus a Pydantic model that rejects bad ADR JSON from Claude before anything is written.

**Spec** — the model's fields are `DESIGN.md` §4. Enforce:
1. Unknown keys fail.
2. No empty or whitespace-only strings.
3. `status`: `provisional` | `accepted` | `superseded-by-NNNN` (4 digits).
4. `options_considered`: at least 2 options, each with a name and a summary.
5. `chosen` equals one option's name exactly.
6. `upgrade_trigger` required only when `status` is `provisional`.
7. `source`: `kind` (`transcript` | `pr` | `inferred`) plus a `ref` whose format depends on `kind`:
   - transcript: `<session_id>:L12` or `<session_id>:L12-30`
   - pr: `#42` or a URL
   - inferred: one or more commit SHAs
8. `date` is a real date.

Plus a `validate` CLI: reads JSON (file or stdin), exits 0 and prints normalized JSON when valid, exits 1 and prints errors as JSON when not, and can print the model's JSON Schema. Commit the generated schema to `schemas/`.

**Acceptance:**
- One passing payload; one failing case per rule, via `parametrize`.
- CLI exit codes tested.
- A test that fails if `schemas/decision.schema.json` drifts from the model.
- The gate passes.

**Pre-check:** rules 1–4 and 8 need no custom code; 5–7 do. What do 5–7 have in common? Should `source` be one string or a nested model, and why?

**Concepts:** validation at a trust boundary; field constraints vs model validators; one source of truth (schema generated from code).
**LLM tooling:** structured outputs — never trust model output unvalidated.

**Mastery check:** why are errors printed as JSON, not prose? What breaks if `extra` is left at its default? Why test schema drift instead of hand-writing the schema?

### Step 2 — ADR writer
**Goal:** validated `Decision` → `docs/decisions/NNNN-slug.md`.

**Spec:**
- Next number = highest existing `NNNN-*.md` + 1. Gaps are allowed; non-ADR files are ignored.
- Slug: lowercase, hyphen-separated, max 60 characters, with a fallback for a title that produces an empty slug.
- Output: YAML frontmatter (number, title, date, status, source, upgrade trigger if present) + Markdown sections (context, options with the chosen one marked, chosen, tradeoffs, upgrade trigger).
- Never overwrite an existing file. Invalid input writes nothing.
- CLI: reads JSON, prints the written path; `--root` to target another directory (needed by tests).

**Acceptance:** tests for slug edge cases, numbering after a gap, ignoring non-ADR files, rendered content, and "invalid input → no `docs/` created".

**Pre-check:** how can you write YAML frontmatter safely without adding a YAML library? How do you make "create, but fail if it exists" a single operation?

**Concepts:** safe file creation; frontmatter as machine-readable metadata.
**LLM tooling:** context engineering — future Claude sessions will Grep and Read these ADRs, so their format is a prompt input.

**Mastery check:** what race exists between computing the next number and creating the file? Why is it acceptable here, and what would make it unacceptable?

### Step 3 — `SessionEnd` hook + queue
**Goal:** when any session ends in an opted-in project, copy its transcript to `.course/transcripts/<session_id>.jsonl` and append an entry to `.course/staged/queue.jsonl`. No LLM call.

**Spec:**
- `init`: create the `.course/` dirs and a `.course/.gitignore` containing `transcripts/` (transcripts may contain secrets).
- `session-end`: read the hook JSON from stdin; do nothing unless `<cwd>/.course/` exists; copy the transcript; enqueue `{session_id, ended_at}`.
- A resumed session ends again: re-copy (the transcript grew), but keep one queue entry.
- `queue`: list pending ids. `done <ids…>`: remove them.
- The hook must never break session exit: catch errors, print to stderr, exit 0.
- `hooks/hooks.json` registers the command.

**Acceptance:** tests for copy + queue, dedupe on resume, an opted-out project left untouched, `done`, and a missing transcript not crashing. Run the hook command once by hand with fake stdin.

**Pre-check:** open one of your own transcripts in `~/.claude/projects/` and count the entry types (`type` field, and content block types). Read the `SessionEnd` input schema in the hooks reference: which fields will you use?

**Concepts:** fail-open vs fail-closed; append-only logs (JSONL); opt-in side effects.
**LLM tooling:** Claude Code hooks — lifecycle events, stdin contract, `${CLAUDE_PLUGIN_ROOT}`.

**Mastery check:** the hook swallows all exceptions. A user says yesterday's session never got queued. Where do you look, and what about this design makes it harder to debug? Why copy the transcript at all, instead of storing its path?

### Step 4 — Transcript digest
**Goal:** `transcript FILE` prints `L<n> user|assistant: <text>`, conversation text only.

**Spec:**
- `<n>` is the JSONL line number. Citations (`<session_id>:L<n>`) depend on it.
- Keep user and assistant text. Drop tool calls, tool results, thinking, meta entries and non-message entries.
- Strip `<system-reminder>`-style tags from text.
- Cap each message's length; mark truncation.
- Skip a malformed line (a partly written last line) instead of crashing.

**Acceptance:** a fixture with every entry type → exact expected output; a truncation test. Measure size before and after on a real transcript.

**Pre-check:** why stream the file line by line (a generator) instead of loading it all?

**Concepts:** generators; defensive parsing of an undocumented format.
**LLM tooling:** token budgeting — prompt efficiency is a product feature here.

**Mastery check:** what decision-relevant information could the digest lose? How would you detect that it lost something important?

### Step 5 — Skills
**Goal:** `skills/learning-curve/SKILL.md` and `skills/decision/SKILL.md`.

**Spec — `learning-curve`:**
1. Init if `.course/` is missing; tell the user what is now captured.
2. For each queued session: digest it (never read the raw transcript); check existing ADR titles to avoid duplicates; extract candidates.
3. A candidate needs at least two alternatives weighed (or disagreement) and a choice, all visible in the digest. Never invent options or rationale. Zero candidates is valid.
4. Each candidate passes `validate` before the user sees it.
5. Show all candidates; the user confirms, edits or rejects each. Nothing is written without confirmation.
6. Write confirmed ones with the ADR CLI; mark sessions done.
7. Flag a candidate that reverses an existing ADR; offer to mark the old one superseded.

**Spec — `decision`:** ask only for missing fields; don't fill gaps with your own rationale; cite a PR or commit if given, else this session (`${CLAUDE_SESSION_ID}`); validate; write on the user's OK.

**Acceptance:** run both by hand in Step 6; every rule above is observable in the transcript of that run.

**Pre-check:** what goes in the frontmatter `description`, and why does its wording matter more than the body's for triggering? What does `allowed-tools` restrict?

**Concepts:** human-in-the-loop as a hallucination guard; least privilege.
**LLM tooling:** skill authoring — frontmatter, placeholders, progressive disclosure, prompt precision.

**Mastery check:** list the hallucination guards across the whole flow (prompt, schema, citation format, human). Which one is weakest, and why?

### Step 6 — Plugin manifest + live test
**Goal:** `.claude-plugin/plugin.json`, then load the plugin for real.

```bash
claude auth login
```
```bash
claude --plugin-dir ~/work/learning-curve
```

**Verify:**
- `/learning-curve` creates `.course/`.
- End the session; the transcript copy and queue entry exist.
- Next session: the review proposes decisions with valid citations.
- `/learning-curve:decision` either fills in `${CLAUDE_SESSION_ID}` or shows it literally. Record which in `DESIGN.md` open question 15.
- Time how long session exit takes with the hook.

**Phase 0 exit:** this repo's own design decisions are ADRs in `docs/decisions/`, written through your plugin.

**Mastery check:** what does `--plugin-dir` do differently from installing through a marketplace? Where did the hook's stderr go during your test?

---

## 4. How each design choice was derived

Basis:
- **Background:** your decisions from the planning session.
- **Inferred:** my reasoning, no external source. Challenge these first.
- **Checked:** verified in docs, local files, or by running something.
- **Memory:** my prior knowledge, not re-verified.

| Choice | Basis | How it was derived | Residual risk |
|---|---|---|---|
| Phase 0 = decision log first | Inferred | Background says the skill must be active from project start; chapters and quizzes both consume ADRs. The log is the one piece everything depends on and the only one useful alone. | You may prefer a thin end-to-end slice instead. |
| Defer extraction; hook only copies + queues | Background | You chose it after weighing token cost against quiz readiness. | Queue can sit unread (open question 14). |
| Copy transcripts into `.course/` | Inferred + Memory | Deferring is only safe if the transcript still exists later. From memory, Claude Code deletes old transcripts after `cleanupPeriodDays` (default 30). | Default not confirmed this session; check the settings doc. |
| Plugin, not a bare skill | Checked | Local plugin-dev docs show plugins ship `hooks/hooks.json` with `${CLAUDE_PLUGIN_ROOT}`; a skill alone has no place to register a `SessionEnd` hook. | Low. |
| `${CLAUDE_PLUGIN_ROOT}` / `${CLAUDE_SKILL_DIR}` in skills | Checked | Grepped installed marketplace skills: 176 and 11 uses. | Low. |
| `${CLAUDE_SESSION_ID}` in `/decision` | Checked (partly) | Skills doc names it as a placeholder and lists cases where placeholders are not substituted. Not tested live. | Step 6 tests it. |
| Hook input fields | Checked + Memory | Hooks doc has a "SessionEnd input" section with `transcript_path`; `session_id` and `cwd` from memory. | Read the schema in Step 3. |
| Digest keeps only user/assistant text | Checked | Counted entry types in one real transcript: text, tool use, tool results, thinking, plus metadata types. Decisions are argued in text. | Internal format; can change without notice. |
| Digest size reduction | Checked | One transcript: 1.6 MB → 11 KB. | One sample. |
| Validation errors as JSON | Inferred | Claude fixes its own output from the error; field paths are easier to act on than prose. | Low. |
| Citation formats | Inferred + Checked | Mandatory citations come from your risk list (hallucinated decisions). 7 hex chars is git's usual shortest abbreviated SHA; 40 is full SHA-1 (gitrevisions). | Rejects SHA-256 repos (64 hex). |
| `chosen` must equal an option name | Inferred | Makes "is the choice among the options?" checkable. | Claude must copy names exactly. |
| Frontmatter without a YAML library | Checked | YAML 1.2 is a superset of JSON. | Some YAML 1.1 parsers differ on edge cases. |
| No-overwrite file creation | Checked | Python `open()` docs: exclusive creation mode. | Low. |
| `uv run --project ${CLAUDE_PLUGIN_ROOT}` | Checked | Ran end to end from another directory during the earlier scaffold. | Needs `uv` installed; first-run latency untested. |
