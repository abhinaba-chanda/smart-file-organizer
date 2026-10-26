"""Loading and validating the YAML configuration."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Optional

import yaml

MODES = ("type", "date", "type-date")
CONFIG_NAME = "organizer.yaml"
DUPLICATE_ACTIONS = ("keep", "move")
_SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([KMGT]?B?)\s*$", re.IGNORECASE)
_UNITS = {"": 1, "B": 1, "K": 1024, "KB": 1024, "M": 1024**2, "MB": 1024**2,
          "G": 1024**3, "GB": 1024**3, "T": 1024**4, "TB": 1024**4}


class ConfigError(ValueError):
    """Raised when the configuration file is invalid."""


def parse_size(value: Any) -> Optional[int]:
    """Parse ``"10MB"``, ``"1.5 GB"`` or ``2048`` into bytes (``None`` stays ``None``)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    m = _SIZE_RE.match(str(value))
    if not m:
        raise ConfigError(f"Cannot understand size '{value}'. Use e.g. 500KB, 10MB or 1GB.")
    return int(float(m.group(1)) * _UNITS[m.group(2).upper()])


@dataclass
class Rule:
    """One sorting rule: files that match go to ``folder``."""

    name: str
    folder: str
    extensions: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    min_size: Optional[int] = None
    max_size: Optional[int] = None

    def matches(self, filename: str, size: int) -> bool:
        """True if a file with this name and size matches the rule."""
        if self.min_size is not None and size < self.min_size:
            return False
        if self.max_size is not None and size > self.max_size:
            return False
        has_name_test = bool(self.extensions or self.patterns)
        if not has_name_test:
            return self.min_size is not None or self.max_size is not None
        lower = filename.lower()
        ext = lower.rsplit(".", 1)[-1] if "." in lower else ""
        if ext and ext in self.extensions:
            return True
        return any(fnmatch.fnmatch(lower, p.lower()) for p in self.patterns)


@dataclass
class Config:
    """The whole configuration."""

    rules: list[Rule]
    mode: str = "type"
    date_format: str = "{year}/{month:02d}"
    other_folder: str = "Other"
    skip_hidden: bool = True
    ignore: list[str] = field(default_factory=list)
    duplicates: str = "keep"
    duplicates_folder: str = "Duplicates"

    def category_for(self, filename: str, size: int) -> tuple[str, str]:
        """Return ``(rule name, folder)`` for a file; unmatched files go to ``other_folder``."""
        for rule in self.rules:
            if rule.matches(filename, size):
                return rule.name, rule.folder
        return "Other", self.other_folder

    def is_ignored(self, filename: str) -> bool:
        """True if the file should be left alone."""
        if self.skip_hidden and filename.startswith("."):
            return True
        lower = filename.lower()
        return any(fnmatch.fnmatch(lower, p.lower()) for p in self.ignore)

    def top_level_folders(self) -> set[str]:
        """First path part of every destination folder (used to skip already-sorted folders)."""
        names = {r.folder.replace("\\", "/").split("/")[0] for r in self.rules}
        return names | {self.other_folder, self.duplicates_folder}


def default_config_text() -> str:
    """The bundled default YAML, as text."""
    return resources.files("smart_organizer").joinpath("default_config.yaml").read_text(encoding="utf-8")


def _rule_from_dict(raw: dict[str, Any], index: int) -> Rule:
    if not isinstance(raw, dict):
        raise ConfigError(f"Rule #{index + 1} must be a mapping with at least 'name' and 'folder'.")
    missing = [k for k in ("name", "folder") if not raw.get(k)]
    if missing:
        raise ConfigError(f"Rule #{index + 1} is missing: {', '.join(missing)}")
    unknown = set(raw) - {"name", "folder", "extensions", "patterns", "min_size", "max_size"}
    if unknown:
        raise ConfigError(f"Rule '{raw['name']}' has unknown keys: {', '.join(sorted(unknown))}")
    exts = [str(e).lower().lstrip(".") for e in raw.get("extensions") or []]
    folder = str(raw["folder"]).replace("\\", "/").strip("/")
    if folder.startswith("..") or "/../" in f"/{folder}/":
        raise ConfigError(f"Rule '{raw['name']}': folder must stay inside the organized folder")
    return Rule(name=str(raw["name"]), folder=folder, extensions=exts,
                patterns=[str(p) for p in raw.get("patterns") or []],
                min_size=parse_size(raw.get("min_size")), max_size=parse_size(raw.get("max_size")))


def config_from_dict(data: dict[str, Any]) -> Config:
    """Build and validate a :class:`Config` from parsed YAML."""
    if not isinstance(data, dict):
        raise ConfigError("The config file must be a YAML mapping.")
    rules = [_rule_from_dict(r, i) for i, r in enumerate(data.get("rules") or [])]
    mode = str(data.get("mode", "type"))
    if mode not in MODES:
        raise ConfigError(f"mode must be one of {', '.join(MODES)} (got '{mode}')")
    dup = str(data.get("duplicates", "keep"))
    if dup not in DUPLICATE_ACTIONS:
        raise ConfigError(f"duplicates must be one of {', '.join(DUPLICATE_ACTIONS)} (got '{dup}')")
    cfg = Config(rules=rules, mode=mode, date_format=str(data.get("date_format", "{year}/{month:02d}")),
                 other_folder=str(data.get("other_folder", "Other")),
                 skip_hidden=bool(data.get("skip_hidden", True)),
                 ignore=[str(p) for p in data.get("ignore") or []],
                 duplicates=dup, duplicates_folder=str(data.get("duplicates_folder", "Duplicates")))
    try:
        cfg.date_format.format(year=2026, month=1, day=1, month_name="January")
    except (KeyError, ValueError, IndexError) as exc:
        raise ConfigError(f"Bad date_format '{cfg.date_format}': {exc}") from exc
    return cfg


def load_config(path: Optional[Path] = None) -> Config:
    """Load a YAML config file, or the bundled defaults when ``path`` is None."""
    text = default_config_text() if path is None else Path(path).read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML: {exc}") from exc
    return config_from_dict(data)


def find_config(folder: Path, explicit: Optional[str] = None) -> Optional[Path]:
    """An explicit file wins; otherwise use organizer.yaml in the folder if present (else built-in rules)."""
    if explicit:
        return Path(explicit).expanduser()
    local = Path(folder) / CONFIG_NAME
    return local if local.is_file() else None
