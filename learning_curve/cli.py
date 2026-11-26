"""Input and error helpers shared by the CLIs."""

import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import ValidationError

from learning_curve.models import Decision

# Error dicts with `type`, `loc` and `msg`, the shape of Pydantic's `errors()`.
Errors = Sequence[Mapping[str, object]]


def fail(errors: Errors) -> int:
    """Print `errors` as JSON and return exit code 1."""
    print(json.dumps({"errors": errors}, indent=2))
    return 1


def load_decision(file: str | None) -> Decision | Errors:
    """Read and validate a Decision payload from `file`, or stdin if None.

    Returns the Decision, or errors for `fail`: `io_error`, `json_invalid`, or Pydantic's.
    """
    try:
        text = Path(file).read_text(encoding="utf-8") if file else sys.stdin.read()
        return Decision.model_validate(json.loads(text))
    except (OSError, UnicodeDecodeError) as e:
        return [{"type": "io_error", "loc": [], "msg": str(e)}]
    except json.JSONDecodeError as e:
        return [{"type": "json_invalid", "loc": [], "msg": str(e)}]
    except ValidationError as e:
        # Without context: `ctx` can hold exception objects that json.dumps rejects.
        return e.errors(include_url=False, include_context=False)
