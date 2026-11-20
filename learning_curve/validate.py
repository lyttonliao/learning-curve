import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import ValidationError

from learning_curve.models import Decision


def _fail(errors: Sequence[Mapping[str, object]]) -> int:
    """Print `errors` as JSON under an "errors" key and return exit code 1."""
    print(json.dumps({"errors": errors}, indent=2))
    return 1


def main(argv: Sequence[str]) -> int:
    """Validate one Decision JSON payload and return a process exit code.

    Reads the payload from the file in `argv`, or from stdin if none is given.
    Valid: prints the normalized JSON, returns 0. Invalid or unreadable: prints
    the errors as JSON, returns 1. With `--schema`: prints the Decision JSON
    Schema and returns 0 without reading any input.

    Returns the code instead of exiting so tests can call it directly. Bad
    command-line usage is the exception: argparse exits with code 2.
    """
    parser = argparse.ArgumentParser(description="Validate a Decision JSON payload.")
    parser.add_argument("file", nargs="?", help="JSON file; reads stdin if omitted")
    parser.add_argument("--schema", action="store_true", help="print JSON Schema")
    args = parser.parse_args(argv)

    # Must come before the stdin read: with no pipe, reading stdin would hang.
    if args.schema:
        print(json.dumps(Decision.model_json_schema(), indent=2))
        return 0

    try:
        if args.file:
            text = Path(args.file).read_text(encoding="utf-8")
        else:
            text = sys.stdin.read()
        decision = Decision.model_validate(json.loads(text))
    except (OSError, UnicodeDecodeError) as e:
        return _fail([{"type": "io_error", "loc": [], "msg": str(e)}])
    except json.JSONDecodeError as e:
        return _fail([{"type": "json_invalid", "loc": [], "msg": str(e)}])
    except ValidationError as e:
        # include_context=False: ctx can hold exception objects json.dumps rejects.
        return _fail(e.errors(include_url=False, include_context=False))

    print(decision.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
