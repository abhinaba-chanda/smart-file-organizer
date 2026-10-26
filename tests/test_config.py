from pathlib import Path

import pytest

from smart_organizer.config import ConfigError, Rule, config_from_dict, load_config, parse_size


def test_default_config_loads():
    cfg = load_config()
    assert cfg.mode == "type"
    assert any(r.name == "Images" for r in cfg.rules)
    assert cfg.category_for("cat.PNG", 10) == ("Images", "Images")
    assert cfg.category_for("Screenshot 1.png", 10)[0] == "Screenshots"
    assert cfg.category_for("thing.unknown", 10) == ("Other", "Other")


@pytest.mark.parametrize("text,expected", [("10", 10), ("1KB", 1024), ("1.5 MB", 1572864), ("2gb", 2 * 1024**3),
                                           (512, 512), (None, None)])
def test_parse_size(text, expected):
    assert parse_size(text) == expected


def test_parse_size_rejects_garbage():
    with pytest.raises(ConfigError):
        parse_size("ten megabytes")


def test_rule_matching_by_size_only():
    big = Rule(name="Big", folder="Big", min_size=100)
    assert big.matches("anything.bin", 150)
    assert not big.matches("anything.bin", 50)


def test_custom_yaml(tmp_path: Path):
    p = tmp_path / "rules.yaml"
    p.write_text(
        "mode: type-date\n"
        "date_format: '{year}-{month:02d}'\n"
        "rules:\n"
        "  - name: Barca\n"
        "    folder: Football/Barca\n"
        "    patterns: ['*barca*', '*messi*']\n"
        "  - name: Pics\n"
        "    folder: Pics\n"
        "    extensions: ['.JPG', png]\n",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.mode == "type-date"
    assert cfg.category_for("messi_goal.mp4", 1) == ("Barca", "Football/Barca")
    assert cfg.category_for("x.jpg", 1) == ("Pics", "Pics")


@pytest.mark.parametrize("data,message", [
    ({"mode": "alphabetical"}, "mode"),
    ({"duplicates": "delete"}, "duplicates"),
    ({"rules": [{"name": "x"}]}, "missing"),
    ({"rules": [{"name": "x", "folder": "y", "colour": "red"}]}, "unknown"),
    ({"rules": [{"name": "x", "folder": "../outside"}]}, "inside"),
    ({"date_format": "{century}"}, "date_format"),
])
def test_invalid_configs(data, message):
    with pytest.raises(ConfigError, match=message):
        config_from_dict(data)


def test_windows_style_folder_is_normalised():
    cfg = config_from_dict({"rules": [{"name": "Docs", "folder": "Documents\\Work", "extensions": ["pdf"]}]})
    assert cfg.rules[0].folder == "Documents/Work"
