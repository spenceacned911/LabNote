from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


TEXT_EXTENSIONS = {
    ".md",
    ".markdown",
    ".mdown",
    ".mkd",
    ".mdx",
    ".txt",
    ".rst",
    ".text",
}

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "dist",
    "build",
    "venv",
    ".venv",
    "__pycache__",
}


@dataclass(slots=True)
class SearchMatch:
    file_path: Path
    line_number: int
    line_text: str

    @property
    def display(self) -> str:
        return f"{self.file_path}:{self.line_number}  {self.line_text.strip()}"


class ProjectSearcher:
    def search(self, root: Path, query: str, max_results: int = 200) -> list[SearchMatch]:
        normalized = query.strip()
        if not normalized or not root.exists() or not root.is_dir():
            return []

        lowered = normalized.casefold()
        results: list[SearchMatch] = []
        for file_path in self._iter_candidate_files(root):
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    content = file_path.read_text(encoding="latin-1")
                except OSError:
                    continue
            except OSError:
                continue

            for line_number, line_text in enumerate(content.splitlines(), start=1):
                if lowered in line_text.casefold():
                    results.append(SearchMatch(file_path=file_path, line_number=line_number, line_text=line_text))
                    if len(results) >= max_results:
                        return results
        return results

    def _iter_candidate_files(self, root: Path):
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in EXCLUDED_DIRS for part in path.parts):
                continue
            if path.suffix.lower() in TEXT_EXTENSIONS:
                yield path
