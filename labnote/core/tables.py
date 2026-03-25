from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


_TABLE_SEPARATOR_RE = re.compile(r":?-{3,}:?")


def display_width(text: str) -> int:
    width = 0
    for char in text:
        if unicodedata.east_asian_width(char) in {"W", "F"}:
            width += 2
        else:
            width += 1
    return width


def pad_display(text: str, width: int) -> str:
    return text + " " * max(0, width - display_width(text))


def split_table_row(line: str) -> list[str]:
    raw = line.strip().strip("|")
    return [cell.strip() for cell in raw.split("|")]


def has_table_shape(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped and "|" in stripped and not stripped.startswith("```"))


def is_separator_line(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(_TABLE_SEPARATOR_RE.fullmatch(cell.replace(" ", "")) for cell in cells)


def parse_alignment(cell: str) -> str:
    normalized = cell.replace(" ", "")
    if normalized.startswith(":") and normalized.endswith(":"):
        return "center"
    if normalized.endswith(":"):
        return "right"
    return "left"


def alignment_marker(alignment: str, width: int) -> str:
    base = "-" * max(3, width)
    if alignment == "center":
        return f":{base}:"
    if alignment == "right":
        return f"{base}:"
    return f":{base}" if width > 3 and alignment == "left-strong" else base


@dataclass(slots=True)
class MarkdownTable:
    start_line: int
    end_line: int
    headers: list[str]
    rows: list[list[str]]
    aligns: list[str]

    @property
    def column_count(self) -> int:
        return max(1, len(self.headers))

    def normalize(self) -> None:
        column_count = self.column_count
        while len(self.headers) < column_count:
            self.headers.append("")
        while len(self.aligns) < column_count:
            self.aligns.append("left")
        self.headers = self.headers[:column_count]
        self.aligns = self.aligns[:column_count]
        self.rows = [self._normalized_row(row, column_count) for row in self.rows]

    def add_row(self) -> None:
        self.normalize()
        self.rows.append([""] * self.column_count)

    def add_column(self, header: str = "") -> None:
        self.normalize()
        self.headers.append(header)
        self.aligns.append("left")
        for row in self.rows:
            row.append("")

    def delete_row(self, index: int) -> None:
        if 0 <= index < len(self.rows):
            self.rows.pop(index)

    def delete_column(self, index: int) -> None:
        if self.column_count <= 1:
            return
        if 0 <= index < self.column_count:
            self.headers.pop(index)
            if index < len(self.aligns):
                self.aligns.pop(index)
            for row in self.rows:
                if index < len(row):
                    row.pop(index)

    def to_markdown(self) -> str:
        self.normalize()
        rows = [self.headers] + self.rows
        widths = [0] * self.column_count
        for row in rows:
            for idx, value in enumerate(self._normalized_row(row, self.column_count)):
                widths[idx] = max(widths[idx], display_width(value), 3)

        def fmt(row: list[str]) -> str:
            normalized = self._normalized_row(row, self.column_count)
            return "| " + " | ".join(pad_display(value, widths[idx]) for idx, value in enumerate(normalized)) + " |"

        separator = "| " + " | ".join(alignment_marker(self.aligns[idx], widths[idx]) for idx in range(self.column_count)) + " |"
        body = [fmt(self.headers), separator]
        body.extend(fmt(row) for row in self.rows)
        return "\n".join(body)

    def _normalized_row(self, row: list[str], column_count: int) -> list[str]:
        padded = list(row[:column_count])
        while len(padded) < column_count:
            padded.append("")
        return padded


class MarkdownTableParser:
    def find_at_cursor(self, text: str, line_number: int) -> MarkdownTable | None:
        lines = text.splitlines()
        if not lines:
            return None
        cursor = max(0, min(line_number - 1, len(lines) - 1))

        for separator_index in range(max(1, cursor - 30), min(len(lines) - 1, cursor + 30) + 1):
            if not is_separator_line(lines[separator_index]):
                continue
            header_index = separator_index - 1
            if header_index < 0 or not has_table_shape(lines[header_index]):
                continue
            end_index = separator_index
            while end_index + 1 < len(lines) and has_table_shape(lines[end_index + 1]):
                end_index += 1
            if header_index <= cursor <= end_index:
                return self.parse_block(lines[header_index : end_index + 1], header_index + 1)
        return None

    def parse_block(self, block_lines: list[str], start_line: int) -> MarkdownTable:
        headers = split_table_row(block_lines[0])
        aligns = [parse_alignment(cell) for cell in split_table_row(block_lines[1])]
        if len(aligns) < len(headers):
            aligns.extend(["left"] * (len(headers) - len(aligns)))
        rows = [split_table_row(line) for line in block_lines[2:] if line.strip()]
        table = MarkdownTable(
            start_line=start_line,
            end_line=start_line + len(block_lines) - 1,
            headers=headers,
            rows=rows,
            aligns=aligns,
        )
        table.normalize()
        return table
