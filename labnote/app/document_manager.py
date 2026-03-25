from __future__ import annotations

import locale
import os
from pathlib import Path
from typing import Iterable

from labnote.core.document import DocumentState


DEFAULT_ENCODINGS = [
    "utf-8",
    "utf-8-sig",
    locale.getpreferredencoding(False) or "utf-8",
    "latin-1",
]


def detect_line_ending(text: str) -> str:
    if "\r\n" in text:
        return "\r\n"
    if "\r" in text:
        return "\r"
    return "\n"


def normalize_line_endings(text: str, line_ending: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.replace("\n", line_ending)


class DocumentManager:
    def __init__(self) -> None:
        self._documents: dict[str, DocumentState] = {}
        self._active_id: str | None = None
        self._untitled_counter = 1

    def new_document(self, title: str | None = None) -> DocumentState:
        resolved_title = title or f"Untitled {self._untitled_counter}"
        self._untitled_counter += 1
        document = DocumentState(title=resolved_title)
        self._documents[document.id] = document
        self._active_id = document.id
        return document

    def open_file(self, path: str | Path) -> DocumentState:
        file_path = Path(path).expanduser().resolve()
        existing = self.find_by_path(file_path)
        if existing:
            self._active_id = existing.id
            return existing

        content, encoding = self._read_text(file_path)
        document = DocumentState(
            path=file_path,
            title=file_path.name,
            content=content,
            encoding=encoding,
            line_ending=detect_line_ending(content),
            last_external_mtime=self._get_mtime(file_path),
        )
        document.mark_clean()
        self._documents[document.id] = document
        self._active_id = document.id
        return document

    def save_document(self, document: DocumentState, target_path: str | Path | None = None) -> DocumentState:
        save_path = Path(target_path).expanduser().resolve() if target_path else document.path
        if save_path is None:
            raise ValueError("A target path is required for untitled documents.")

        line_ending = document.line_ending or os.linesep
        content = normalize_line_endings(document.content, line_ending)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(content, encoding=document.encoding or "utf-8")
        document.path = save_path
        document.title = save_path.name
        document.content = content
        document.last_external_mtime = self._get_mtime(save_path)
        document.mark_clean()
        return document

    def reload_from_disk(self, document: DocumentState) -> DocumentState:
        if not document.path:
            return document
        content, encoding = self._read_text(document.path)
        document.content = content
        document.encoding = encoding
        document.line_ending = detect_line_ending(content)
        document.last_external_mtime = self._get_mtime(document.path)
        document.mark_clean()
        return document

    def close_document(self, document_id: str) -> DocumentState | None:
        document = self._documents.pop(document_id, None)
        if document and self._active_id == document_id:
            self._active_id = next(iter(self._documents.keys()), None)
        return document

    def find_by_path(self, path: Path) -> DocumentState | None:
        normalized = path.expanduser().resolve()
        for document in self._documents.values():
            if document.path and document.path == normalized:
                return document
        return None

    def get(self, document_id: str) -> DocumentState | None:
        return self._documents.get(document_id)

    def all_documents(self) -> list[DocumentState]:
        return list(self._documents.values())

    def set_active(self, document_id: str | None) -> None:
        self._active_id = document_id

    def active_document(self) -> DocumentState | None:
        return self._documents.get(self._active_id) if self._active_id else None

    def restore_session(self, paths: Iterable[str]) -> list[DocumentState]:
        restored: list[DocumentState] = []
        for raw_path in paths:
            try:
                restored.append(self.open_file(raw_path))
            except OSError:
                continue
        return restored

    def _read_text(self, path: Path) -> tuple[str, str]:
        last_error: OSError | None = None
        for encoding in DEFAULT_ENCODINGS:
            try:
                return path.read_text(encoding=encoding), encoding
            except (UnicodeDecodeError, OSError) as exc:
                last_error = exc if isinstance(exc, OSError) else last_error
                continue
        if last_error:
            raise last_error
        return path.read_text(encoding="utf-8", errors="replace"), "utf-8"

    def _get_mtime(self, path: Path) -> float | None:
        try:
            return path.stat().st_mtime
        except OSError:
            return None
