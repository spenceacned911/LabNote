from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class _TabWidgets:
    frame: tk.Frame
    title_button: tk.Button
    close_button: tk.Button


class CloseableTabBar(tk.Frame):
    def __init__(self, master: tk.Misc, on_select: Callable[[str], None], on_close: Callable[[str], None]) -> None:
        super().__init__(master, highlightthickness=0, borderwidth=0)
        self.on_select = on_select
        self.on_close = on_close
        self.theme: dict[str, str] = {}
        self.active_id: str | None = None
        self._tabs: dict[str, _TabWidgets] = {}

        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, height=44)
        self.inner = tk.Frame(self.canvas, highlightthickness=0, borderwidth=0)
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.scrollbar = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview, width=10)
        self.canvas.configure(xscrollcommand=self.scrollbar.set)
        self.canvas.pack(fill="both", expand=True, side="top")
        self.scrollbar.pack(fill="x", side="bottom")

        self.inner.bind("<Configure>", self._sync_region)
        self.canvas.bind("<Configure>", self._stretch_inner)
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_wheel, add="+")

    def set_theme(self, theme: dict[str, str]) -> None:
        self.theme = theme
        self.configure(bg=theme["toolbar_bg"])
        self.canvas.configure(bg=theme["toolbar_bg"], highlightbackground=theme["toolbar_bg"])
        self.inner.configure(bg=theme["toolbar_bg"])
        self.scrollbar.configure(
            bg=theme["surface_alt"],
            activebackground=theme["surface_deep"],
            troughcolor=theme["toolbar_bg"],
            highlightbackground=theme["toolbar_bg"],
            bd=0,
            relief="flat",
        )
        self._refresh_tab_styles()

    def add_tab(self, document_id: str, title: str) -> None:
        if document_id in self._tabs:
            self.update_title(document_id, title)
            return
        frame = tk.Frame(self.inner, highlightthickness=1, borderwidth=0, padx=6, pady=4, cursor="hand2")
        title_button = tk.Button(frame, text=title, command=lambda doc_id=document_id: self.on_select(doc_id), bd=0, relief="flat", padx=10, pady=6, anchor="w", cursor="hand2")
        close_button = tk.Button(frame, text="×", command=lambda doc_id=document_id: self.on_close(doc_id), bd=0, relief="flat", padx=8, pady=4, cursor="hand2")
        title_button.pack(side="left")
        close_button.pack(side="left", padx=(2, 0))
        frame.pack(side="left", padx=(0, 8), pady=4)
        for widget in (frame, title_button):
            widget.bind("<Button-1>", lambda _event, doc_id=document_id: self.on_select(doc_id))
        self._tabs[document_id] = _TabWidgets(frame=frame, title_button=title_button, close_button=close_button)
        self._refresh_tab_styles()
        self.after_idle(lambda: self.canvas.xview_moveto(1.0))

    def remove_tab(self, document_id: str) -> None:
        widgets = self._tabs.pop(document_id, None)
        if widgets:
            widgets.frame.destroy()
        if self.active_id == document_id:
            self.active_id = None
        self._refresh_tab_styles()

    def update_title(self, document_id: str, title: str) -> None:
        widgets = self._tabs.get(document_id)
        if widgets:
            widgets.title_button.configure(text=title)

    def select(self, document_id: str | None) -> None:
        self.active_id = document_id
        self._refresh_tab_styles()

    def _refresh_tab_styles(self) -> None:
        if not self.theme:
            return
        for document_id, widgets in self._tabs.items():
            active = document_id == self.active_id
            bg = self.theme["tab_active_bg"] if active else self.theme["tab_inactive_bg"]
            fg = self.theme["text"] if active else self.theme["text_soft"]
            border = self.theme["accent"] if active else self.theme["border"]
            widgets.frame.configure(bg=bg, highlightbackground=border)
            widgets.title_button.configure(bg=bg, fg=fg, activebackground=self.theme["tab_hover_bg"], activeforeground=self.theme["text"], highlightthickness=0)
            widgets.close_button.configure(bg=bg, fg=self.theme["text_soft"], activebackground=self.theme["accent_soft"], activeforeground=self.theme["danger"], highlightthickness=0)

    def _sync_region(self, _event: tk.Event | None = None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _stretch_inner(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.window_id, height=event.height)

    def _on_shift_wheel(self, event: tk.Event) -> None:
        if not self.winfo_ismapped():
            return
        delta = -1 if event.delta > 0 else 1
        self.canvas.xview_scroll(delta, "units")
