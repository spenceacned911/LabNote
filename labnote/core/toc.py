from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(slots=True)
class HeadingEntry:
    level: int
    text: str
    line_number: int
    anchor: str


class TableOfContentsExtractor:
    def extract(self, ast_nodes: list[dict], source_text: str) -> list[HeadingEntry]:
        headings: list[HeadingEntry] = []
        heading_texts = [self._collect_text(node.get("children", [])) for node in ast_nodes if node.get("type") == "heading"]
        heading_lines = self._find_heading_lines(source_text, heading_texts)
        heading_index = 0

        for node in ast_nodes:
            if node.get("type") != "heading":
                continue
            level = int(node.get("attrs", {}).get("level", 1))
            text = self._collect_text(node.get("children", [])) or "Untitled heading"
            line_number = heading_lines[heading_index] if heading_index < len(heading_lines) else 1
            headings.append(
                HeadingEntry(
                    level=level,
                    text=text,
                    line_number=line_number,
                    anchor=self._slugify(text),
                )
            )
            heading_index += 1

        return headings

    def _find_heading_lines(self, source_text: str, heading_texts: Iterable[str]) -> list[int]:
        lines = source_text.splitlines()
        results: list[int] = []
        start_index = 0
        for heading in heading_texts:
            normalized_heading = " ".join(heading.split()).strip()
            found = False
            for idx in range(start_index, len(lines)):
                candidate = lines[idx].strip()
                stripped = candidate.lstrip("#").strip() if candidate.startswith("#") else candidate
                if normalized_heading and normalized_heading == " ".join(stripped.split()).strip():
                    results.append(idx + 1)
                    start_index = idx + 1
                    found = True
                    break
            if not found:
                results.append(1)
        return results

    def _collect_text(self, nodes: list[dict]) -> str:
        parts: list[str] = []
        for node in nodes:
            node_type = node.get("type")
            if node_type == "text":
                parts.append(node.get("raw", ""))
            elif node_type in {"codespan", "inline_math"}:
                parts.append(node.get("raw", ""))
            elif "children" in node:
                parts.append(self._collect_text(node["children"]))
            elif node_type == "image":
                parts.append(node.get("attrs", {}).get("alt", "image"))
        return "".join(parts)

    def _slugify(self, text: str) -> str:
        slug = []
        for char in text.lower().strip():
            if char.isalnum():
                slug.append(char)
            elif char in {" ", "-", "_"}:
                slug.append("-")
        compact = "".join(slug).strip("-")
        while "--" in compact:
            compact = compact.replace("--", "-")
        return compact or "section"
