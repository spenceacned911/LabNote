from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from uuid import uuid4


@dataclass(slots=True)
class DocumentState:
    id: str = field(default_factory=lambda: uuid4().hex)
    path: Optional[Path] = None
    content: str = ""
    dirty: bool = False
    encoding: str = "utf-8"
    line_ending: str = "\n"
    cursor_index: str = "1.0"
    title: str = "Untitled"
    last_external_mtime: Optional[float] = None

    @property
    def display_name(self) -> str:
        return self.path.name if self.path else self.title

    @property
    def full_display_name(self) -> str:
        return str(self.path) if self.path else self.title

    def mark_clean(self) -> None:
        self.dirty = False

    def mark_dirty(self) -> None:
        self.dirty = True
