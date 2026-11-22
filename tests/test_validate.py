import io
import json
from pathlib import Path
from typing import Any

import pytest

from learning_curve.models import Decision
from learning_curve.validate import main
from tests.test_models import GOOD


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    """Call `main(argv)` and return (exit code, printed stdout parsed as JSON)."""
    code = main(argv)
    return code, json.loads(capsys.readouterr().out)


def test_schema_flag(capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run(["--schema"], capsys)
    assert code == 0
    assert out["title"] == "Decision"


def test_valid_file_prints_normalized_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "decision.json"
    path.write_text(json.dumps(GOOD))
    code, out = run([str(path)], capsys)
    assert code == 0
    assert out == GOOD


def test_valid_stdin(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(GOOD)))
    code, out = run([], capsys)
    assert code == 0
    assert out == GOOD


def test_invalid_payload_reports_field(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "decision.json"
    path.write_text(json.dumps({**GOOD, "title": "   "}))
    code, out = run([str(path)], capsys)
    assert code == 1
    assert out["errors"][0]["loc"] == ["title"]


SCHEMA_FILE = Path(__file__).parent.parent / "schemas" / "decision.schema.json"


@pytest.mark.parametrize(
    ("content", "error_type"),
    [
        (b"{", "json_invalid"),
        (b"\xff\xfe", "io_error"),  # not UTF-8
        (None, "io_error"),  # file never created
    ],
)
def test_unreadable_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    content: bytes | None,
    error_type: str,
) -> None:
    path = tmp_path / "input.json"
    if content is not None:
        path.write_bytes(content)
    code, out = run([str(path)], capsys)
    assert code == 1
    assert out["errors"][0]["type"] == error_type


def test_unknown_flag_exits_2() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--bogus"])
    assert exc.value.code == 2


def test_committed_schema_matches_model() -> None:
    committed = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    assert committed == Decision.model_json_schema()
