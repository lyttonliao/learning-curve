from pathlib import Path

from learning_curve.adr import slugify, yaml_str
from learning_curve.models import Concept


def render_concept(concept: Concept) -> str:
    """Render `concept` as a Markdown note with YAML frontmatter.

    Frontmatter strings go through `yaml_str`, like the ADR renderer, so `:` or `"` in a title
    cannot breka the YAML. Misconception and alternatives are omitted when absent.
    """
    sources = ", ".join(
        f"{{kind: {yaml_str(s.kind)}, ref: {yaml_str(s.ref)}}}" for s in concept.sources
    )
    front = [
        "---",
        f"title: {yaml_str(concept.title)}",
        f"kind: {yaml_str(concept.kind)}",
        f"importance: {concept.importance}",
        f"session_id: {yaml_str(concept.session_id)}",
        f"sources: [{sources}]",
        f"tags: [{', '.join(yaml_str(t) for t in concept.tags)}]",
        "---",
    ]
    body = [
        f"# {concept.title}",
        "",
        "## Explanation",
        "",
        concept.explanation,
        "",
        "## Why it came up",
        "",
        concept.why_it_came_up,
        "",
    ]
    if concept.misconception:
        body += ["## Misconception", "", concept.misconception, ""]
    if concept.alternatives:
        options = [f"- **{o.name}**: {o.summary}" for o in concept.alternatives]
        body += ["## Alternatives", "", *options, ""]
    return "\n".join([*front, "", *body])


def write_concept(concept: Concept, root: Path) -> Path:
    """Write `concept` to `<root>/docs/concepts/<slug>.md` if and return the path.

    Never overwrites: mode "x" raises `FileExistsError` if the note exists, so re-extracting
    a session cannot duplicate or clobber a note.
    """
    directory = root / "docs" / "concepts"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{slugify(concept.title)}.md"
    with path.open("x", encoding="utf-8") as f:
        f.write(render_concept(concept))
    return path
