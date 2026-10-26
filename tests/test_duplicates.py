from pathlib import Path

from smart_organizer.duplicates import file_hash, find_duplicates


def test_finds_identical_content(tmp_path: Path):
    a, b, c = tmp_path / "a.bin", tmp_path / "b.bin", tmp_path / "c.bin"
    a.write_bytes(b"same" * 1000)
    b.write_bytes(b"same" * 1000)
    c.write_bytes(b"diff" * 1000)
    groups = find_duplicates([a, b, c])
    assert len(groups) == 1 and {p.name for p in groups[0]} == {"a.bin", "b.bin"}


def test_same_size_same_head_different_tail(tmp_path: Path):
    head = b"x" * (64 * 1024)
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_bytes(head + b"tail-one")
    b.write_bytes(head + b"tail-two")
    assert find_duplicates([a, b]) == []


def test_large_identical_files(tmp_path: Path):
    data = bytes(range(256)) * 5000  # > 1 MB chunk boundary
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_bytes(data)
    b.write_bytes(data)
    assert len(find_duplicates([a, b])) == 1
    assert file_hash(a) == file_hash(b)


def test_empty_files_are_not_duplicates(tmp_path: Path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_bytes(b"")
    b.write_bytes(b"")
    assert find_duplicates([a, b]) == []
