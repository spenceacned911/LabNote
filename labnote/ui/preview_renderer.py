from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from typing import Any


class PreviewTextRenderer:
    def __init__(self, widget: tk.Text) -> None:
        self.widget = widget
        self.theme: dict[str, str] = {}
        self._link_counter = 0
        self._link_targets: dict[str, str] = {}
        self._fonts: dict[str, tkfont.Font] = {}
        self._embedded_widgets: list[tk.Widget] = []

    def apply_theme(self, theme: dict[str, str], font_size: int, code_font_size: int, line_spacing: int) -> None:
        self.theme = theme
        base_family = tkfont.nametofont("TkDefaultFont").actual("family")
        mono_family = "Consolas" if self.widget.tk.call("tk", "windowingsystem") == "win32" else "Courier"
        self._fonts = {
            "body": tkfont.Font(family=base_family, size=font_size),
            "body_bold": tkfont.Font(family=base_family, size=font_size, weight="bold"),
            "body_italic": tkfont.Font(family=base_family, size=font_size, slant="italic"),
            "body_bold_italic": tkfont.Font(family=base_family, size=font_size, weight="bold", slant="italic"),
            "h1": tkfont.Font(family=base_family, size=font_size + 12, weight="bold"),
            "h2": tkfont.Font(family=base_family, size=font_size + 9, weight="bold"),
            "h3": tkfont.Font(family=base_family, size=font_size + 6, weight="bold"),
            "h4": tkfont.Font(family=base_family, size=font_size + 4, weight="bold"),
            "h5": tkfont.Font(family=base_family, size=font_size + 2, weight="bold"),
            "h6": tkfont.Font(family=base_family, size=font_size + 1, weight="bold"),
            "code": tkfont.Font(family=mono_family, size=code_font_size),
        }
        self.widget.configure(
            bg=theme["preview_bg"],
            fg=theme["text"],
            insertbackground=theme["text"],
            wrap="word",
            relief="flat",
            borderwidth=0,
            padx=28,
            pady=24,
            selectbackground=theme["selection"],
            selectforeground=theme["text"],
            font=self._fonts["body"],
        )
        self._configure_tags(line_spacing)

    def render(self, ast_nodes: list[dict[str, Any]]) -> None:
        self.widget.configure(state="normal")
        self._destroy_embedded_widgets()
        self.widget.delete("1.0", "end")
        self._link_counter = 0
        self._link_targets.clear()
        for node in ast_nodes:
            self._render_block(node)
        self.widget.insert("end", "\n")
        self.widget.configure(state="disabled")

    def _destroy_embedded_widgets(self) -> None:
        for child in self._embedded_widgets:
            if child.winfo_exists():
                child.destroy()
        self._embedded_widgets.clear()

    def _configure_tags(self, line_spacing: int) -> None:
        self.widget.tag_configure("body", font=self._fonts["body"], foreground=self.theme["text"], spacing3=line_spacing)
        self.widget.tag_configure("strong", font=self._fonts["body_bold"])
        self.widget.tag_configure("em", font=self._fonts["body_italic"])
        self.widget.tag_configure("strong_em", font=self._fonts["body_bold_italic"])
        self.widget.tag_configure("strike", overstrike=True)
        self.widget.tag_configure("inline_code", font=self._fonts["code"], background=self.theme["code_bg"], foreground=self.theme["text"])
        self.widget.tag_configure("code_block", font=self._fonts["code"], background=self.theme["code_bg"], foreground=self.theme["text"], lmargin1=14, lmargin2=14, rmargin=12, spacing1=6, spacing3=10)
        self.widget.tag_configure("blockquote", foreground=self.theme["text_soft"], background=self.theme["quote_bg"], lmargin1=18, lmargin2=18, rmargin=8, spacing1=4, spacing3=8)
        self.widget.tag_configure("bullet", foreground=self.theme["accent"], font=self._fonts["body_bold"])
        self.widget.tag_configure("link", foreground=self.theme["link"], underline=True)
        self.widget.tag_configure("math", foreground=self.theme["accent"], font=self._fonts["code"])
        self.widget.tag_configure("muted", foreground=self.theme["text_muted"])
        for level in range(1, 7):
            self.widget.tag_configure(f"h{level}", font=self._fonts[f"h{level}"], foreground=self.theme["text"], spacing1=14, spacing3=6)

    def _render_block(self, node: dict[str, Any], depth: int = 0) -> None:
        node_type = node.get("type")
        if node_type == "heading":
            level = min(int(node.get("attrs", {}).get("level", 1)), 6)
            self._render_inlines(node.get("children", []), base_tags=(f"h{level}",))
            self._insert("\n\n")
        elif node_type == "paragraph":
            self._render_inlines(node.get("children", []), base_tags=("body",))
            self._insert("\n\n")
        elif node_type == "block_code":
            info = (node.get("attrs", {}).get("info") or "").strip()
            if info:
                self._insert(f"[{info}]\n", ("muted", "code_block"))
            self._insert(node.get("raw", ""), ("code_block",))
            if not node.get("raw", "").endswith("\n"):
                self._insert("\n", ("code_block",))
            self._insert("\n")
        elif node_type == "list":
            ordered = bool(node.get("attrs", {}).get("ordered", False))
            for idx, child in enumerate(node.get("children", []), start=1):
                self._render_list_item(child, depth=depth, ordered=ordered, index=idx)
            self._insert("\n")
        elif node_type == "block_quote":
            for child in node.get("children", []):
                if child.get("type") == "paragraph":
                    self._insert("│ ", ("blockquote",))
                    self._render_inlines(child.get("children", []), base_tags=("blockquote",))
                    self._insert("\n\n")
                else:
                    self._render_block(child, depth=depth + 1)
        elif node_type == "table":
            self._render_table(node)
            self._insert("\n")
        elif node_type == "thematic_break":
            self._insert("─" * 42 + "\n\n", ("muted",))
        elif node_type == "footnotes":
            self._insert("Footnotes\n", ("h3",))
            for idx, footnote in enumerate(node.get("children", []), start=1):
                self._insert(f"[{idx}] ", ("bullet",))
                for child in footnote.get("children", []):
                    if child.get("type") == "paragraph":
                        self._render_inlines(child.get("children", []), base_tags=("body",))
                        self._insert("\n")
            self._insert("\n")

    def _render_list_item(self, node: dict[str, Any], depth: int, ordered: bool, index: int) -> None:
        indent = "    " * depth
        prefix = f"{index}. " if ordered else "• "
        if node.get("type") == "task_list_item":
            checked = bool(node.get("attrs", {}).get("checked", False))
            prefix = "[x] " if checked else "[ ] "

        rendered = False
        for child in node.get("children", []):
            child_type = child.get("type")
            if child_type in {"block_text", "paragraph"}:
                self._insert(indent + prefix, ("bullet",))
                self._render_inlines(child.get("children", []), base_tags=("body",))
                self._insert("\n")
                rendered = True
            elif child_type == "list":
                self._render_block(child, depth=depth + 1)
            else:
                self._insert(indent + (" " * len(prefix)), ("body",))
                self._render_block(child, depth=depth + 1)
                rendered = True
        if not rendered:
            self._insert(indent + prefix + "\n", ("bullet",))

    def _render_table(self, node: dict[str, Any]) -> None:
        rows: list[list[str]] = []
        for child in node.get("children", []):
            if child.get("type") == "table_head":
                rows.append([self._collect_text(cell.get("children", [])) for cell in child.get("children", [])])
            elif child.get("type") == "table_body":
                for row in child.get("children", []):
                    rows.append([self._collect_text(cell.get("children", [])) for cell in row.get("children", [])])
        if not rows:
            return
        column_count = max(len(row) for row in rows)
        table_frame = tk.Frame(self.widget, bg=self.theme["border"], highlightthickness=1, highlightbackground=self.theme["border"], bd=0)
        for column in range(column_count):
            table_frame.columnconfigure(column, weight=1)
        for row_index, row in enumerate(rows):
            padded = list(row)
            while len(padded) < column_count:
                padded.append("")
            for column_index, value in enumerate(padded):
                label = tk.Label(
                    table_frame,
                    text=value or " ",
                    justify="left",
                    anchor="w",
                    bg=self.theme["surface_alt"] if row_index == 0 else self.theme["surface"],
                    fg=self.theme["text"],
                    padx=10,
                    pady=7,
                    font=self._fonts["body_bold"] if row_index == 0 else self._fonts["body"],
                    wraplength=260,
                )
                label.grid(row=row_index, column=column_index, sticky="nsew", padx=1, pady=1)
        self._embedded_widgets.append(table_frame)
        self.widget.window_create("end", window=table_frame)
        self._insert("\n\n")

    def _render_inlines(self, nodes: list[dict[str, Any]], base_tags: tuple[str, ...] = ()) -> None:
        for node in nodes:
            node_type = node.get("type")
            if node_type == "text":
                self._insert(node.get("raw", ""), base_tags)
            elif node_type in {"softbreak", "linebreak"}:
                self._insert("\n", base_tags)
            elif node_type == "strong":
                tags = base_tags + (("strong_em",) if "em" in base_tags else ("strong",))
                self._render_inlines(node.get("children", []), tags)
            elif node_type == "emphasis":
                tags = base_tags + (("strong_em",) if "strong" in base_tags else ("em",))
                self._render_inlines(node.get("children", []), tags)
            elif node_type == "strikethrough":
                self._render_inlines(node.get("children", []), base_tags + ("strike",))
            elif node_type == "codespan":
                self._insert(node.get("raw", ""), base_tags + ("inline_code",))
            elif node_type in {"inline_math", "block_math"}:
                self._insert(node.get("raw", ""), base_tags + ("math",))
            elif node_type == "link":
                url = node.get("attrs", {}).get("url", "")
                link_text = self._collect_text(node.get("children", [])) or url
                tag_name = f"link_{self._link_counter}"
                self._link_counter += 1
                self._link_targets[tag_name] = url
                self.widget.tag_bind(tag_name, "<Button-1>", lambda _event, key=tag_name: self._open_link(key))
                self.widget.tag_bind(tag_name, "<Enter>", lambda _event: self.widget.configure(cursor="hand2"))
                self.widget.tag_bind(tag_name, "<Leave>", lambda _event: self.widget.configure(cursor="xterm"))
                self._insert(link_text, base_tags + ("link", tag_name))
            elif node_type == "image":
                alt = node.get("attrs", {}).get("alt", "image")
                url = node.get("attrs", {}).get("url", "")
                self._insert(f"[Image: {alt}] {url}", base_tags + ("muted",))
            elif node_type == "footnote_ref":
                self._insert(f"[{node.get('raw', '')}]", base_tags + ("muted",))
            elif "children" in node:
                self._render_inlines(node.get("children", []), base_tags)

    def _collect_text(self, nodes: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        for node in nodes:
            node_type = node.get("type")
            if node_type == "text":
                parts.append(node.get("raw", ""))
            elif node_type in {"codespan", "inline_math", "block_math"}:
                parts.append(node.get("raw", ""))
            elif node_type == "image":
                parts.append(node.get("attrs", {}).get("alt", "image"))
            elif "children" in node:
                parts.append(self._collect_text(node.get("children", [])))
        return "".join(parts)

    def _insert(self, text: str, tags: tuple[str, ...] = ()) -> None:
        if text:
            self.widget.insert("end", text, tags)

    def _open_link(self, tag_name: str) -> None:
        url = self._link_targets.get(tag_name)
        if url:
            webbrowser.open(url)
