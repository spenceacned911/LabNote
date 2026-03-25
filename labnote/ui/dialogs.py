from __future__ import annotations

from copy import deepcopy
import tkinter as tk
from tkinter import ttk

from labnote.app.commands import CommandRegistry
from labnote.app.i18n import I18n, SUPPORTED_LANGUAGES
from labnote.app.settings import AppSettings
from labnote.core.tables import MarkdownTable


class CommandPalette(tk.Toplevel):
    def __init__(self, master: tk.Misc, registry: CommandRegistry, i18n: I18n) -> None:
        super().__init__(master)
        self.registry = registry
        self.i18n = i18n
        self.title(self.i18n.tr("command_palette"))
        self.transient(master.winfo_toplevel())
        self.geometry("760x460")
        self.minsize(560, 360)
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda _event: self.close())
        self.bind("<Return>", lambda _event: self.execute_selected())

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.query_var = tk.StringVar()
        self.query_var.trace_add("write", lambda *_args: self.refresh())

        self.entry = ttk.Entry(self, textvariable=self.query_var)
        self.entry.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 10))

        self.listbox = tk.Listbox(self, activestyle="none", borderwidth=0, highlightthickness=0)
        self.listbox.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        self.listbox.bind("<Double-Button-1>", lambda _event: self.execute_selected())

        self.hint = ttk.Label(self, text=self.i18n.tr("command_hint"), style="Muted.TLabel")
        self.hint.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))

        self._commands = []
        self.refresh()
        self.after(30, self.entry.focus_set)

    def open(self) -> None:
        self.deiconify()
        self.lift()
        self.grab_set()
        self.entry.focus_set()

    def refresh(self) -> None:
        self.listbox.delete(0, "end")
        self._commands = self.registry.search(self.query_var.get())
        for command in self._commands:
            suffix = f"    [{command.shortcut}]" if command.shortcut else ""
            self.listbox.insert("end", f"{command.description}{suffix}")
        if self._commands:
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(0)
            self.listbox.activate(0)

    def execute_selected(self) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        command = self._commands[selection[0]]
        self.close()
        self.registry.execute(command.id)

    def close(self) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()


class PreferencesDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, settings: AppSettings, theme_names: list[str], i18n: I18n) -> None:
        super().__init__(master)
        self.result: AppSettings | None = None
        self.i18n = i18n
        self.title(self.i18n.tr("pref_title"))
        self.transient(master.winfo_toplevel())
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.bind("<Escape>", lambda _event: self.cancel())

        body = ttk.Frame(self, padding=18)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)

        self.theme_var = tk.StringVar(value=settings.theme_name)
        self.language_var = tk.StringVar(value=settings.language)
        self.font_size_var = tk.IntVar(value=settings.font_size)
        self.code_font_size_var = tk.IntVar(value=settings.code_font_size)
        self.line_spacing_var = tk.IntVar(value=settings.line_spacing)
        self.auto_save_var = tk.BooleanVar(value=settings.auto_save)
        self.auto_save_delay_var = tk.IntVar(value=settings.auto_save_delay_ms)
        self.restore_session_var = tk.BooleanVar(value=settings.restore_session)
        self.show_sidebar_var = tk.BooleanVar(value=settings.show_sidebar)
        self.layout_mode_var = tk.StringVar(value=settings.layout_mode)
        self.focus_mode_var = tk.BooleanVar(value=settings.focus_mode)
        self.typewriter_mode_var = tk.BooleanVar(value=settings.typewriter_mode)

        row = 0
        self._add_label(body, row, self.i18n.tr("pref_theme"))
        ttk.Combobox(body, textvariable=self.theme_var, values=theme_names, state="readonly").grid(row=row, column=1, sticky="ew", pady=4)
        row += 1
        self._add_label(body, row, self.i18n.tr("pref_language"))
        language_values = list(SUPPORTED_LANGUAGES.keys())
        language_combo = ttk.Combobox(body, textvariable=self.language_var, values=language_values, state="readonly")
        language_combo.grid(row=row, column=1, sticky="ew", pady=4)
        row += 1
        self._add_label(body, row, self.i18n.tr("pref_font_size"))
        ttk.Spinbox(body, from_=11, to=28, textvariable=self.font_size_var, width=8).grid(row=row, column=1, sticky="w", pady=4)
        row += 1
        self._add_label(body, row, self.i18n.tr("pref_code_font_size"))
        ttk.Spinbox(body, from_=11, to=24, textvariable=self.code_font_size_var, width=8).grid(row=row, column=1, sticky="w", pady=4)
        row += 1
        self._add_label(body, row, self.i18n.tr("pref_line_spacing"))
        ttk.Spinbox(body, from_=2, to=12, textvariable=self.line_spacing_var, width=8).grid(row=row, column=1, sticky="w", pady=4)
        row += 1
        self._add_label(body, row, self.i18n.tr("pref_layout"))
        ttk.Combobox(body, textvariable=self.layout_mode_var, values=["split", "editor", "preview"], state="readonly").grid(row=row, column=1, sticky="w", pady=4)
        row += 1
        ttk.Checkbutton(body, text=self.i18n.tr("pref_auto_save"), variable=self.auto_save_var).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1
        self._add_label(body, row, self.i18n.tr("pref_auto_save_delay"))
        ttk.Spinbox(body, from_=1000, to=10000, increment=500, textvariable=self.auto_save_delay_var, width=8).grid(row=row, column=1, sticky="w", pady=4)
        row += 1
        ttk.Checkbutton(body, text=self.i18n.tr("pref_restore_session"), variable=self.restore_session_var).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1
        ttk.Checkbutton(body, text=self.i18n.tr("pref_show_sidebar"), variable=self.show_sidebar_var).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1
        ttk.Checkbutton(body, text=self.i18n.tr("pref_focus_mode"), variable=self.focus_mode_var).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1
        ttk.Checkbutton(body, text=self.i18n.tr("pref_typewriter_mode"), variable=self.typewriter_mode_var).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1

        button_bar = ttk.Frame(body)
        button_bar.grid(row=row, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(button_bar, text=self.i18n.tr("cancel_button"), command=self.cancel).pack(side="right", padx=(8, 0))
        ttk.Button(button_bar, text=self.i18n.tr("save_button"), style="Accent.TButton", command=self.save).pack(side="right")

        self.update_idletasks()
        self.grab_set()
        self.focus_set()

    def save(self) -> None:
        self.result = AppSettings(
            theme_name=self.theme_var.get(),
            language=self.language_var.get(),
            font_size=int(self.font_size_var.get()),
            code_font_size=int(self.code_font_size_var.get()),
            line_spacing=int(self.line_spacing_var.get()),
            auto_save=bool(self.auto_save_var.get()),
            auto_save_delay_ms=int(self.auto_save_delay_var.get()),
            restore_session=bool(self.restore_session_var.get()),
            show_sidebar=bool(self.show_sidebar_var.get()),
            layout_mode=self.layout_mode_var.get(),
            focus_mode=bool(self.focus_mode_var.get()),
            typewriter_mode=bool(self.typewriter_mode_var.get()),
        )
        self.destroy()

    def cancel(self) -> None:
        self.result = None
        self.destroy()

    def _add_label(self, parent: ttk.Frame, row: int, text: str) -> None:
        ttk.Label(parent, text=text).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=4)


class TableEditorDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, table: MarkdownTable, i18n: I18n) -> None:
        super().__init__(master)
        self.i18n = i18n
        self.result: MarkdownTable | None = None
        self.table = deepcopy(table)
        self.title(self.i18n.tr("table_editor_title"))
        self.transient(master.winfo_toplevel())
        self.geometry("920x620")
        self.minsize(760, 460)
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.bind("<Escape>", lambda _event: self.cancel())
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        top = ttk.Frame(self, padding=(18, 18, 18, 10))
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)
        ttk.Label(top, text=self.i18n.tr("table_editor_hint"), style="Muted.TLabel", wraplength=760, justify="left").grid(row=0, column=0, sticky="w")
        ttk.Label(top, text=self.i18n.tr("table_preview_note"), style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(6, 0))

        tools = ttk.Frame(self, padding=(18, 0, 18, 10))
        tools.grid(row=2, column=0, sticky="ew")
        ttk.Button(tools, text=self.i18n.tr("add_row"), command=self.add_row).pack(side="left")
        ttk.Button(tools, text=self.i18n.tr("add_column"), command=self.add_column).pack(side="left", padx=(8, 0))
        ttk.Label(tools, text=self.i18n.tr("row_index")).pack(side="left", padx=(18, 6))
        self.row_index_var = tk.IntVar(value=max(1, len(self.table.rows)))
        ttk.Spinbox(tools, from_=1, to=max(1, len(self.table.rows)), textvariable=self.row_index_var, width=5).pack(side="left")
        ttk.Button(tools, text=self.i18n.tr("delete_row"), command=self.delete_row).pack(side="left", padx=(8, 0))
        ttk.Label(tools, text=self.i18n.tr("column_index")).pack(side="left", padx=(18, 6))
        self.column_index_var = tk.IntVar(value=max(1, self.table.column_count))
        ttk.Spinbox(tools, from_=1, to=max(1, self.table.column_count), textvariable=self.column_index_var, width=5).pack(side="left")
        ttk.Button(tools, text=self.i18n.tr("delete_column"), command=self.delete_column).pack(side="left", padx=(8, 0))

        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=18)
        self.scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_y.grid(row=1, column=1, sticky="ns", pady=0)
        self.canvas.configure(yscrollcommand=self.scroll_y.set)
        self.grid_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.grid_frame.bind("<Configure>", self._sync_scroll_region)
        self.canvas.bind("<Configure>", self._sync_frame_width)

        buttons = ttk.Frame(self, padding=18)
        buttons.grid(row=3, column=0, sticky="e")
        ttk.Button(buttons, text=self.i18n.tr("table_cancel"), command=self.cancel).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text=self.i18n.tr("table_save"), style="Accent.TButton", command=self.save).pack(side="right")

        self.header_vars: list[tk.StringVar] = []
        self.body_vars: list[list[tk.StringVar]] = []
        self._rebuild_grid()
        self.grab_set()
        self.focus_set()

    def add_row(self) -> None:
        self._harvest_vars()
        self.table.add_row()
        self.row_index_var.set(len(self.table.rows))
        self._rebuild_grid()

    def add_column(self) -> None:
        self._harvest_vars()
        self.table.add_column()
        self.column_index_var.set(self.table.column_count)
        self._rebuild_grid()

    def delete_row(self) -> None:
        self._harvest_vars()
        self.table.delete_row(max(0, int(self.row_index_var.get()) - 1))
        self.row_index_var.set(max(1, min(int(self.row_index_var.get()), max(1, len(self.table.rows)))))
        self._rebuild_grid()

    def delete_column(self) -> None:
        self._harvest_vars()
        self.table.delete_column(max(0, int(self.column_index_var.get()) - 1))
        self.column_index_var.set(max(1, min(int(self.column_index_var.get()), self.table.column_count)))
        self._rebuild_grid()

    def save(self) -> None:
        self._harvest_vars()
        self.table.normalize()
        self.result = self.table
        self.destroy()

    def cancel(self) -> None:
        self.result = None
        self.destroy()

    def _rebuild_grid(self) -> None:
        self.table.normalize()
        for child in self.grid_frame.winfo_children():
            child.destroy()

        self.header_vars = []
        self.body_vars = []

        ttk.Label(self.grid_frame, text=self.i18n.tr("table_headers"), style="Heading.TLabel").grid(row=0, column=0, sticky="w", padx=6, pady=(0, 8))
        for column_index in range(self.table.column_count):
            ttk.Label(self.grid_frame, text=self.i18n.tr("table_column", index=column_index + 1), style="Muted.TLabel").grid(row=0, column=column_index + 1, sticky="w", padx=6, pady=(0, 8))
            header_var = tk.StringVar(value=self.table.headers[column_index])
            entry = ttk.Entry(self.grid_frame, textvariable=header_var)
            entry.grid(row=1, column=column_index + 1, sticky="ew", padx=6, pady=4)
            self.header_vars.append(header_var)
            self.grid_frame.columnconfigure(column_index + 1, weight=1)

        for row_index, row in enumerate(self.table.rows, start=0):
            ttk.Label(self.grid_frame, text=self.i18n.tr("table_row", index=row_index + 1), style="Muted.TLabel").grid(row=row_index + 2, column=0, sticky="w", padx=6, pady=4)
            row_vars: list[tk.StringVar] = []
            for column_index in range(self.table.column_count):
                value = row[column_index] if column_index < len(row) else ""
                body_var = tk.StringVar(value=value)
                entry = ttk.Entry(self.grid_frame, textvariable=body_var)
                entry.grid(row=row_index + 2, column=column_index + 1, sticky="ew", padx=6, pady=4)
                row_vars.append(body_var)
            self.body_vars.append(row_vars)

    def _harvest_vars(self) -> None:
        self.table.headers = [variable.get() for variable in self.header_vars]
        self.table.rows = [[variable.get() for variable in row] for row in self.body_vars]
        self.table.normalize()

    def _sync_scroll_region(self, _event: tk.Event | None = None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _sync_frame_width(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.canvas_window, width=event.width)


def show_preferences(master: tk.Misc, settings: AppSettings, theme_names: list[str], i18n: I18n) -> AppSettings | None:
    dialog = PreferencesDialog(master, settings=settings, theme_names=theme_names, i18n=i18n)
    master.wait_window(dialog)
    return dialog.result


def show_table_editor(master: tk.Misc, table: MarkdownTable, i18n: I18n) -> MarkdownTable | None:
    dialog = TableEditorDialog(master, table=table, i18n=i18n)
    master.wait_window(dialog)
    return dialog.result
