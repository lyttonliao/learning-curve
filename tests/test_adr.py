from pathlib import Path

from learning_curve.adr import next_number


def touch(directory: Path, *names: str) -> None:
    for name in names:
        (directory / name).touch()


def test_empty_or_missing_directory_starts_at_1(tmp_path: Path) -> None:
    assert next_number(tmp_path) == 1
    assert next_number(tmp_path / "nope") == 1


def test_numbering_continues_after_a_gap(tmp_path: Path) -> None:
    touch(tmp_path, "0001-a.md", "0004-b.md")
    assert next_number(tmp_path) == 5


def test_non_adr_files_are_ignored(tmp_path: Path) -> None:
    touch(tmp_path, "README.md", "0009.md", "12-x.md", "0007-x.txt", "0002-ok.md")
    assert next_number(tmp_path) == 3