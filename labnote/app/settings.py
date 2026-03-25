from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass, field
from pathlib import Path

from labnote.ui.themes import DEFAULT_THEME


CONFIG_DIR_NAME = "labnote"
CONFIG_FILE_NAME = "settings.json"


@dataclass(slots=True)
class AppSettings:
    theme_name: str = DEFAULT_THEME
    language: str = "zh-CN"
    font_size: int = 14
    code_font_size: int = 13
    line_spacing: int = 6
    auto_save: bool = False
    auto_save_delay_ms: int = 3000
    restore_session: bool = True
    show_sidebar: bool = True
    layout_mode: str = "split"
    focus_mode: bool = False
    typewriter_mode: bool = False
    recent_files: list[str] = field(default_factory=list)
    last_folder: str = ""
    window_width: int = 1540
    window_height: int = 960
    sidebar_width: int = 320
    editor_split_ratio: float = 0.5
    session_files: list[str] = field(default_factory=list)
    session_active: str = ""


class SettingsStore:
    def __init__(self) -> None:
        self.config_dir = self._default_config_dir()
        self.config_file = self.config_dir / CONFIG_FILE_NAME
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppSettings:
        if not self.config_file.exists():
            return AppSettings()
        try:
            data = json.loads(self.config_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return AppSettings()
        defaults = asdict(AppSettings())
        defaults.update({key: value for key, value in data.items() if key in defaults})
        return AppSettings(**defaults)

    def save(self, settings: AppSettings) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")

    def _default_config_dir(self) -> Path:
        system = platform.system()
        home = Path.home()
        if system == "Windows":
            base = os.environ.get("APPDATA")
            return Path(base) / CONFIG_DIR_NAME if base else home / CONFIG_DIR_NAME
        if system == "Darwin":
            return home / "Library" / "Application Support" / CONFIG_DIR_NAME
        return Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / CONFIG_DIR_NAME
