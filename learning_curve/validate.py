"""Validate a Decision JSON payload, or print the Decision JSON Schema."""

import argparse
import json
import sys
from collections.abc import Sequence

from learning_curve.cli import fail, load_decision
from learning_curve.models import Decision


def main(argv: Sequence[str]) -> int:
    """Validate a Decision payload (file or stdin) and print it normalized.

    Returns 0 when valid, 1 with JSON errors when not. `--schema` prints the JSON Schema
    instead. Returns the code rather than exiting, so tests can call it.
    """
    parser = argparse.ArgumentParser(description="Validate a Decision JSON payload.")
    parser.add_argument("file", nargs="?", help="JSON file; reads stdin if omitted")
    parser.add_argument("--schema", action="store_true", help="print JSON Schema")
    args = parser.parse_args(argv)

    if args.schema:  # before any stdin read, which would hang without a pipe
        print(json.dumps(Decision.model_json_schema(), indent=2))
        return 0

    result = load_decision(args.file)
    if not isinstance(result, Decision):
        return fail(result)
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
