import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import ValidationError

from learning_curve.models import Decision

# JSON-ready error dicts: `type`, `loc`, `msg` (the shape Pydantic's errors() uses).
Errors = Sequence[Mapping[str, object]]


def fail(errors: Errors) -> int:
    """Print `errors` as JSON under an "errors" key and return exit code 1."""
    print(json.dumps({"errors": errors}, indent=2))
    return 1


def load_decision(file: str | None) -> Decision | Errors:
    """Read, parse and validate one Decision payload from `file`, or stdin if None.

    Returns the Decision, or the list of errors for the caller to pass to `fail`.
    """
    try:
        text = Path(file).read_text(encoding="utf-8") if file else sys.stdin.read()
        return Decision.model_validate(json.loads(text))
    except (OSError, UnicodeDecodeError) as e:
        return [{"type": "io_error", "loc": [], "msg": str(e)}]
    except json.JSONDecodeError as e:
        return [{"type": "json_invalid", "loc": [], "msg": str(e)}]
    except ValidationError as e:
        # include_context=False: ctx can hold exception objects json.dumps rejects.
        return e.errors(include_url=False, include_context=False)
