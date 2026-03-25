from __future__ import annotations

import re
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from typing import Callable

from labnote.core.document import DocumentState
from labnote.core.markdown_engine import MarkdownEngine, RenderedMarkdown
from labnote.core.tables import MarkdownTable, MarkdownTableParser
from labnote.ui.preview_renderer import PreviewTextRenderer
from labnote.ui.themes import DEFAULT_THEME, get_theme


StatsPayload = dict[str, int]


class DocumentView(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        document: DocumentState,
        engine: MarkdownEngine,
        on_content_changed: Callable[[DocumentState], None],
        on_rendered: Callable[[DocumentState, RenderedMarkdown], None],
        on_status_update: Callable[[StatsPayload], None],
        on_split_ratio_changed: Callable[[float], None],
    ) -> None:
        super().__init__(master, style="Card.TFrame")
        self.document = document
        self.engine = engine
        self.on_content_changed = on_content_changed
        self.on_rendered = on_rendered
        self.on_status_update = on_status_update
        self.on_split_ratio_changed = on_split_ratio_changed
        self.theme: dict[str, str] = {}
        self.theme_name = "Graphite Dark"
        self.layout_mode = "split"
        self.typewriter_mode = False
        self._preview_job: str | None = None
        self._is_setting_content = False
        self._split_ratio = 0.5
        self._table_parser = MarkdownTableParser()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.paned = ttk.Panedwindow(self, orient="horizontal")
        self.paned.grid(row=0, column=0, sticky="nsew")

        self.editor_frame = ttk.Frame(self, style="Card.TFrame")
        self.editor_frame.rowconfigure(0, weight=1)
        self.editor_frame.columnconfigure(0, weight=1)
        self.preview_frame = ttk.Frame(self, style="Card.TFrame")
        self.preview_frame.rowconfigure(0, weight=1)
        self.preview_frame.columnconfigure(0, weight=1)

        self.editor = tk.Text(
            self.editor_frame,
            undo=True,
            wrap="word",
            borderwidth=0,
            relief="flat",
            padx=24,
            pady=20,
            maxundo=-1,
            autoseparators=True,
        )
        self.editor.grid(row=0, column=0, sticky="nsew")
        self.editor_scroll = ttk.Scrollbar(self.editor_frame, orient="vertical", command=self.editor.yview)
        self.editor_scroll.grid(row=0, column=1, sticky="ns")
        self.editor.configure(yscrollcommand=self.editor_scroll.set)

        self.preview = tk.Text(self.preview_frame, wrap="word", borderwidth=0, relief="flat", state="disabled")
        self.preview.grid(row=0, column=0, sticky="nsew")
        self.preview_scroll = ttk.Scrollbar(self.preview_frame, orient="vertical", command=self.preview.yview)
        self.preview_scroll.grid(row=0, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=self.preview_scroll.set)
        self.preview_renderer = PreviewTextRenderer(self.preview)

        self.paned.add(self.editor_frame, weight=1)
        self.paned.add(self.preview_frame, weight=1)
        self.paned.bind("<ButtonRelease-1>", self._remember_split_ratio, add="+")

        self.editor.bind("<<Modified>>", self._on_editor_modified)
        self.editor.bind("<KeyRelease>", self._on_cursor_activity, add="+")
        self.editor.bind("<ButtonRelease-1>", self._on_cursor_activity, add="+")
        self.editor.bind("<FocusIn>", self._on_cursor_activity, add="+")

        self.set_theme(DEFAULT_THEME, get_theme(DEFAULT_THEME), font_size=14, code_font_size=13, line_spacing=6)
        self.set_content(document.content)

    def set_theme(self, theme_name: str, theme: dict[str, str], font_size: int, code_font_size: int, line_spacing: int) -> None:
        self.theme = theme
        self.theme_name = theme_name
        mono_family = "Consolas" if self.editor.tk.call("tk", "windowingsystem") == "win32" else "Courier"
        editor_font = tkfont.Font(family=mono_family, size=code_font_size)
        self.editor.configure(
            bg=theme["editor_bg"],
            fg=theme["text"],
            insertbackground=theme["text"],
            selectbackground=theme["selection"],
            selectforeground=theme["text"],
            font=editor_font,
            spacing1=2,
            spacing2=line_spacing,
            spacing3=2,
            highlightthickness=0,
        )
        self.editor.tag_configure("current_line", background=theme["editor_line"])
        self.preview_renderer.apply_theme(theme, font_size=font_size, code_font_size=code_font_size, line_spacing=line_spacing)
        self._highlight_current_line()
        self.refresh_preview(immediate=True)

    def set_layout_mode(self, mode: str) -> None:
        self.layout_mode = mode
        panes = list(self.paned.panes())
        editor_name = str(self.editor_frame)
        preview_name = str(self.preview_frame)
        if mode == "editor":
            if preview_name in panes:
                self.paned.forget(self.preview_frame)
            if editor_name not in panes:
                self.paned.add(self.editor_frame, weight=1)
        elif mode == "preview":
            if editor_name in panes:
                self.paned.forget(self.editor_frame)
            if preview_name not in panes:
                self.paned.add(self.preview_frame, weight=1)
        else:
            if editor_name not in panes:
                self.paned.insert(0, self.editor_frame, weight=1)
            if preview_name not in self.paned.panes():
                self.paned.add(self.preview_frame, weight=1)
            self.after_idle(self._apply_split_ratio)

    def set_typewriter_mode(self, enabled: bool) -> None:
        self.typewriter_mode = enabled

    def set_split_ratio(self, ratio: float) -> None:
        self._split_ratio = min(0.82, max(0.18, ratio))
        self.after_idle(self._apply_split_ratio)

    def focus_editor(self) -> None:
        self.editor.focus_set()

    def set_content(self, content: str) -> None:
        self._is_setting_content = True
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", content)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self._is_setting_content = False
        self.refresh_preview(immediate=True)
        self._highlight_current_line()
        self.on_status_update(self.stats_payload())

    def get_content(self) -> str:
        return self.editor.get("1.0", "end-1c")

    def refresh_preview(self, immediate: bool = False) -> None:
        if self._preview_job:
            self.after_cancel(self._preview_job)
            self._preview_job = None
        if immediate:
            self._perform_render()
            return
        self._preview_job = self.after(160, self._perform_render)

    def go_to_line(self, line_number: int) -> None:
        index = f"{max(1, line_number)}.0"
        self.editor.mark_set("insert", index)
        self.editor.see(index)
        self.editor.focus_set()
        self._highlight_current_line()
        self.on_status_update(self.stats_payload())

    def update_document_reference(self, document: DocumentState) -> None:
        self.document = document

    def stats_payload(self) -> StatsPayload:
        content = self.get_content()
        western_words = re.findall(r"[A-Za-z0-9_]+(?:['’-][A-Za-z0-9_]+)?", content)
        cjk_chars = re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", content)
        chars = len(content)
        line, column = self.editor.index("insert").split(".")
        return {
            "words": len(western_words) + len(cjk_chars),
            "chars": chars,
            "line": int(line),
            "column": int(column) + 1,
        }

    def current_cursor_line(self) -> int:
        return int(self.editor.index("insert").split(".")[0])

    def find_current_table(self) -> MarkdownTable | None:
        return self._table_parser.find_at_cursor(self.get_content(), self.current_cursor_line())

    def insert_table_template(self, headers: list[str] | None = None) -> None:
        headers = headers or ["Column 1", "Column 2"]
        table = MarkdownTable(start_line=self.current_cursor_line(), end_line=self.current_cursor_line() + 2, headers=headers, rows=[["Value", "Value"]], aligns=["left"] * len(headers))
        text = table.to_markdown()
        insert_index = self.editor.index("insert linestart")
        self._replace_text_range(insert_index, insert_index, text + "\n")

    def replace_current_table(self, table: MarkdownTable) -> bool:
        if not table:
            return False
        replacement = table.to_markdown()
        start_index = f"{table.start_line}.0"
        end_index = f"{table.end_line}.0 lineend"
        if self.editor.compare(end_index, "<", "end-1c"):
            end_index = f"{table.end_line + 1}.0"
            replacement = replacement + "\n"
        self._replace_text_range(start_index, end_index, replacement)
        self.go_to_line(table.start_line)
        return True

    def format_current_table(self) -> bool:
        table = self.find_current_table()
        if not table:
            return False
        return self.replace_current_table(table)

    def _replace_text_range(self, start_index: str, end_index: str, content: str) -> None:
        self._is_setting_content = True
        self.editor.edit_separator()
        self.editor.delete(start_index, end_index)
        self.editor.insert(start_index, content)
        self.editor.edit_separator()
        self._is_setting_content = False
        self.document.content = self.get_content()
        self.document.mark_dirty()
        self.on_content_changed(self.document)
        self.refresh_preview(immediate=True)
        self.on_status_update(self.stats_payload())
        self._highlight_current_line()

    def _perform_render(self) -> None:
        self._preview_job = None
        rendered = self.engine.render(self.get_content(), theme_name=self.theme_name, title=self.document.display_name)
        self.preview_renderer.render(rendered.ast)
        self.on_rendered(self.document, rendered)

    def _on_editor_modified(self, _event: tk.Event) -> None:
        if self._is_setting_content:
            self.editor.edit_modified(False)
            return
        if self.editor.edit_modified():
            self.document.content = self.get_content()
            self.document.mark_dirty()
            self.on_content_changed(self.document)
            self.refresh_preview(immediate=False)
            self.editor.edit_modified(False)
            self._highlight_current_line()
            self.on_status_update(self.stats_payload())

    def _on_cursor_activity(self, _event: tk.Event | None = None) -> None:
        self._highlight_current_line()
        if self.typewriter_mode:
            self._center_cursor_line()
        self.on_status_update(self.stats_payload())

    def _highlight_current_line(self) -> None:
        if not self.theme:
            return
        self.editor.tag_remove("current_line", "1.0", "end")
        index = self.editor.index("insert")
        line_start = f"{index.split('.')[0]}.0"
        line_end = f"{index.split('.')[0]}.0 lineend+1c"
        self.editor.tag_add("current_line", line_start, line_end)

    def _center_cursor_line(self) -> None:
        line_index = self.editor.index("insert")
        info = self.editor.dlineinfo(line_index)
        if not info:
            return
        widget_height = max(1, self.editor.winfo_height())
        visible_lines = max(1, int(widget_height / max(info[3], 1)))
        line_number = int(line_index.split(".")[0])
        target_top_line = max(1, line_number - visible_lines // 2)
        total_lines = max(1, int(float(self.editor.index("end-1c").split(".")[0])))
        fraction = max(0.0, min(1.0, (target_top_line - 1) / max(total_lines, 1)))
        if abs(self.editor.yview()[0] - fraction) > 0.05:
            self.editor.yview_moveto(fraction)

    def _apply_split_ratio(self) -> None:
        if self.layout_mode != "split" or len(self.paned.panes()) < 2:
            return
        width = self.paned.winfo_width()
        if width <= 10:
            self.after(50, self._apply_split_ratio)
            return
        self.paned.sashpos(0, int(width * self._split_ratio))

    def _remember_split_ratio(self, _event: tk.Event | None = None) -> None:
        if self.layout_mode != "split" or len(self.paned.panes()) < 2:
            return
        width = self.paned.winfo_width()
        if width <= 0:
            return
        self._split_ratio = self.paned.sashpos(0) / width
        self.on_split_ratio_changed(self._split_ratio)
