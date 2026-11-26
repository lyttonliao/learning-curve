from learning_curve.adr import _q
from learning_curve.models import Concept


def render_concept(concept: Concept) -> str:
    """Render `concept` as a Markdown note with YAML frontmatter.

    Frontmatter strings go through `_q`, like the ADR renderer, so `:` or `"` in a title
    cannot breka the YAML. Misconception and alternatives are omitted when absent.
    """
    sources = ", ".join(f"{{kind: {_q(s.kind)}, ref: {_q(s.ref)}}}" for s in concept.sources)
    front = [
        "---",
        f"title: {_q(concept.title)}",
        f"kind: {_q(concept.kind)}",
        f"importance: {concept.importance}",
        f"session_id: {_q(concept.session_id)}",
        f"sources: [{sources}]",
        f"tags: [{', '.join(_q(t) for t in concept.tags)}]",
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
