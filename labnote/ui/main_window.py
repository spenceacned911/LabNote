from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Iterable

from labnote.app.commands import Command, CommandRegistry
from labnote.app.document_manager import DocumentManager
from labnote.app.file_watcher import PollingFileWatcher
from labnote.app.i18n import I18n, SUPPORTED_LANGUAGES
from labnote.app.settings import AppSettings, SettingsStore
from labnote.core.document import DocumentState
from labnote.core.exporters import ExportService
from labnote.core.markdown_engine import MarkdownEngine, RenderedMarkdown
from labnote.core.search import ProjectSearcher, SearchMatch
from labnote.ui.dialogs import CommandPalette, show_preferences, show_table_editor
from labnote.ui.document_view import DocumentView, StatsPayload
from labnote.ui.themes import DEFAULT_THEME, THEMES, apply_theme, get_theme
from labnote.ui.widgets import CloseableTabBar


MARKDOWN_FILETYPES = [
    ("Markdown", "*.md *.markdown *.mdown *.mkd *.mdx"),
    ("Text", "*.txt"),
    ("All files", "*.*"),
]


class MainWindow:
    def __init__(self, root: tk.Tk, settings_store: SettingsStore, settings: AppSettings, startup_paths: Iterable[str] | None = None) -> None:
        self.root = root
        self.settings_store = settings_store
        self.settings = settings
        self.startup_paths = list(startup_paths or [])
        self.i18n = I18n(settings.language)
        self.theme = get_theme(settings.theme_name or DEFAULT_THEME)

        self.engine = MarkdownEngine()
        self.export_service = ExportService(self.engine)
        self.document_manager = DocumentManager()
        self.command_registry = CommandRegistry()
        self.searcher = ProjectSearcher()
        self.file_watcher = PollingFileWatcher(self._notify_external_change)

        self.views: dict[str, DocumentView] = {}
        self.view_order: list[str] = []
        self.rendered_cache: dict[str, RenderedMarkdown] = {}
        self.search_results: list[SearchMatch] = []
        self.current_folder: Path | None = None
        self.active_document_id: str | None = None
        self._search_results_meta: dict[int, SearchMatch] = {}
        self._auto_save_jobs: dict[str, str] = {}
        self._message_job: str | None = None
        self._recent_menu: tk.Menu | None = None
        self._command_palette: CommandPalette | None = None

        self._theme_var = tk.StringVar(value=self.settings.theme_name or DEFAULT_THEME)
        self._language_var = tk.StringVar(value=self.settings.language)
        self.search_var = tk.StringVar()
        self.message_var = tk.StringVar(value=self.tr("ready"))
        self.stats_var = tk.StringVar(value="")
        self.path_var = tk.StringVar(value="")

        self._build_window()
        self._build_ui()
        self._register_commands()
        self._build_menu()
        self._bind_shortcuts()
        self.apply_settings_to_ui()

        self.file_watcher.start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)
        self._open_startup_content()

    def tr(self, key: str, **kwargs: object) -> str:
        return self.i18n.tr(key, **kwargs)

    def _build_window(self) -> None:
        self.root.title(self.tr("app_title"))
        width = max(1120, int(self.settings.window_width or 1540))
        height = max(760, int(self.settings.window_height or 960))
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(1040, 720)
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

    def _build_ui(self) -> None:
        self.topbar = ttk.Frame(self.root, style="Toolbar.TFrame", padding=(16, 14))
        self.topbar.grid(row=0, column=0, sticky="ew")
        self.topbar.columnconfigure(2, weight=1)

        self.brand_label = tk.Label(self.topbar, text="LabNote", padx=12, pady=7, cursor="arrow")
        self.brand_label.grid(row=0, column=0, sticky="w", padx=(0, 14))

        self.action_frame = ttk.Frame(self.topbar, style="Toolbar.TFrame")
        self.action_frame.grid(row=0, column=1, sticky="w")
        self.new_button = ttk.Button(self.action_frame, style="Toolbar.TButton", command=self.new_document)
        self.open_file_button = ttk.Button(self.action_frame, style="Toolbar.TButton", command=self.open_file_dialog)
        self.open_folder_button = ttk.Button(self.action_frame, style="Toolbar.TButton", command=self.open_folder_dialog)
        self.save_button = ttk.Button(self.action_frame, style="Accent.TButton", command=self.save_current_document)
        self.table_button = ttk.Button(self.action_frame, style="Toolbar.TButton", command=self.open_table_editor)
        self.new_button.pack(side="left")
        self.open_file_button.pack(side="left", padx=(8, 0))
        self.open_folder_button.pack(side="left", padx=(8, 0))
        self.save_button.pack(side="left", padx=(8, 0))
        self.table_button.pack(side="left", padx=(8, 0))

        self.mode_frame = ttk.Frame(self.topbar, style="Toolbar.TFrame")
        self.mode_frame.grid(row=0, column=2, sticky="w", padx=(22, 0))
        self.mode_editor_button = ttk.Button(self.mode_frame, command=lambda: self.set_layout_mode("editor"))
        self.mode_split_button = ttk.Button(self.mode_frame, command=lambda: self.set_layout_mode("split"))
        self.mode_preview_button = ttk.Button(self.mode_frame, command=lambda: self.set_layout_mode("preview"))
        self.mode_editor_button.pack(side="left")
        self.mode_split_button.pack(side="left", padx=(8, 0))
        self.mode_preview_button.pack(side="left", padx=(8, 0))

        self.right_tools = ttk.Frame(self.topbar, style="Toolbar.TFrame")
        self.right_tools.grid(row=0, column=3, sticky="e")
        self.theme_label = ttk.Label(self.right_tools, style="Toolbar.TLabel")
        self.theme_label.pack(side="left", padx=(0, 6))
        self.theme_combo = ttk.Combobox(self.right_tools, state="readonly", width=15, textvariable=self._theme_var, values=list(THEMES.keys()))
        self.theme_combo.pack(side="left")
        self.theme_combo.bind("<<ComboboxSelected>>", lambda _event: self.change_theme(self._theme_var.get()))
        self.language_button = ttk.Button(self.right_tools, style="Ghost.TButton", command=self.toggle_language)
        self.language_button.pack(side="left", padx=(10, 0))
        self.palette_button = ttk.Button(self.right_tools, style="Toolbar.TButton", command=self.show_command_palette)
        self.preferences_button = ttk.Button(self.right_tools, style="Toolbar.TButton", command=self.open_preferences)
        self.palette_button.pack(side="left", padx=(10, 0))
        self.preferences_button.pack(side="left", padx=(8, 0))
        self.topbar.grid_remove()

        self.body_paned = ttk.Panedwindow(self.root, orient="horizontal")
        self.body_paned.grid(row=1, column=0, sticky="nsew")
        self.body_paned.bind("<ButtonRelease-1>", self._remember_sidebar_width, add="+")

        self.sidebar = ttk.Frame(self.body_paned, style="Sidebar.TFrame", width=self.settings.sidebar_width)
        self.sidebar.rowconfigure(0, weight=1)
        self.sidebar.columnconfigure(0, weight=1)

        self.sidebar_notebook = ttk.Notebook(self.sidebar)
        self.sidebar_notebook.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self._build_file_tree_panel()
        self._build_toc_panel()
        self._build_search_panel()

        self.workspace = ttk.Frame(self.body_paned, style="TFrame")
        self.workspace.rowconfigure(1, weight=1)
        self.workspace.columnconfigure(0, weight=1)

        self.tabbar = CloseableTabBar(self.workspace, on_select=self.select_document, on_close=self.close_document_by_id)
        self.tabbar.grid(row=0, column=0, sticky="ew")
        self.view_stack = ttk.Frame(self.workspace, style="Card.TFrame")
        self.view_stack.grid(row=1, column=0, sticky="nsew", padx=12, pady=(8, 12))
        self.view_stack.rowconfigure(0, weight=1)
        self.view_stack.columnconfigure(0, weight=1)

        self.body_paned.add(self.sidebar, weight=0)
        self.body_paned.add(self.workspace, weight=1)

        self.status = ttk.Frame(self.root, style="Status.TFrame", padding=(14, 8))
        self.status.grid(row=2, column=0, sticky="ew")
        self.status.columnconfigure(1, weight=1)
        ttk.Label(self.status, textvariable=self.message_var, style="Status.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(self.status, textvariable=self.path_var, style="Status.TLabel").grid(row=0, column=1, sticky="e", padx=(12, 18))
        ttk.Label(self.status, textvariable=self.stats_var, style="Status.TLabel").grid(row=0, column=2, sticky="e")

    def _build_file_tree_panel(self) -> None:
        self.file_tree_panel = ttk.Frame(self.sidebar_notebook, style="Sidebar.TFrame")
        self.file_tree_panel.rowconfigure(1, weight=1)
        self.file_tree_panel.columnconfigure(0, weight=1)
        header = ttk.Frame(self.file_tree_panel, style="Sidebar.TFrame", padding=(8, 8, 8, 4))
        header.grid(row=0, column=0, sticky="ew")
        self.project_label = ttk.Label(header, style="Sidebar.TLabel")
        self.project_label.pack(side="left")
        self.sidebar_open_folder_button = ttk.Button(header, style="Ghost.TButton", command=self.open_folder_dialog)
        self.sidebar_open_folder_button.pack(side="right")
        self.file_tree = ttk.Treeview(self.file_tree_panel, show="tree")
        self.file_tree.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self.file_tree_panel, orient="vertical", command=self.file_tree.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.file_tree.configure(yscrollcommand=scroll.set)
        self.file_tree.bind("<Double-1>", self._open_selected_tree_item)
        self.sidebar_notebook.add(self.file_tree_panel, text=self.tr("project"))

    def _build_toc_panel(self) -> None:
        self.toc_panel = ttk.Frame(self.sidebar_notebook, style="Sidebar.TFrame")
        self.toc_panel.rowconfigure(1, weight=1)
        self.toc_panel.columnconfigure(0, weight=1)
        self.toc_label = ttk.Label(self.toc_panel, style="Sidebar.TLabel", padding=(8, 8))
        self.toc_label.grid(row=0, column=0, sticky="ew")
        self.toc_list = tk.Listbox(self.toc_panel, activestyle="none", borderwidth=0, highlightthickness=0)
        self.toc_list.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self.toc_panel, orient="vertical", command=self.toc_list.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.toc_list.configure(yscrollcommand=scroll.set)
        self.toc_list.bind("<Double-Button-1>", self._jump_to_selected_heading)
        self.sidebar_notebook.add(self.toc_panel, text=self.tr("outline"))

    def _build_search_panel(self) -> None:
        self.search_panel = ttk.Frame(self.sidebar_notebook, style="Sidebar.TFrame")
        self.search_panel.rowconfigure(2, weight=1)
        self.search_panel.columnconfigure(0, weight=1)
        self.search_header_label = ttk.Label(self.search_panel, style="Sidebar.TLabel", padding=(8, 8, 8, 4))
        self.search_header_label.grid(row=0, column=0, sticky="ew")
        self.search_entry = ttk.Entry(self.search_panel, textvariable=self.search_var)
        self.search_entry.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.search_entry.bind("<Return>", lambda _event: self.perform_search())
        self.search_list = tk.Listbox(self.search_panel, activestyle="none", borderwidth=0, highlightthickness=0)
        self.search_list.grid(row=2, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self.search_panel, orient="vertical", command=self.search_list.yview)
        scroll.grid(row=2, column=1, sticky="ns")
        self.search_list.configure(yscrollcommand=scroll.set)
        self.search_list.bind("<Double-Button-1>", self._open_selected_search_result)
        button_bar = ttk.Frame(self.search_panel, style="Sidebar.TFrame", padding=(8, 8))
        button_bar.grid(row=3, column=0, sticky="ew")
        self.search_button = ttk.Button(button_bar, style="Toolbar.TButton", command=self.perform_search)
        self.search_button.pack(side="left")
        self.clear_search_button = ttk.Button(button_bar, style="Ghost.TButton", command=self.clear_search_results)
        self.clear_search_button.pack(side="left", padx=(8, 0))
        self.sidebar_notebook.add(self.search_panel, text=self.tr("search"))

    def apply_settings_to_ui(self) -> None:
        self.theme = apply_theme(self.root, self.settings.theme_name or DEFAULT_THEME)
        self.i18n.set_language(self.settings.language)
        self._theme_var.set(self.settings.theme_name or DEFAULT_THEME)
        self._language_var.set(self.settings.language)
        self._apply_brand_theme()
        self._apply_listbox_theme()
        self.tabbar.set_theme(self.theme)
        self._register_commands()
        self._build_menu()
        self._refresh_texts()
        for view in self.views.values():
            view.set_theme(self.settings.theme_name or DEFAULT_THEME, self.theme, font_size=self.settings.font_size, code_font_size=self.settings.code_font_size, line_spacing=self.settings.line_spacing)
            view.set_layout_mode(self.settings.layout_mode)
            view.set_typewriter_mode(self.settings.typewriter_mode)
            view.set_split_ratio(self.settings.editor_split_ratio)
        self._refresh_mode_buttons()
        self._apply_focus_mode()
        self._apply_sidebar_visibility()
        self._refresh_status_for_current_tab()
        self.root.after(80, self._apply_sidebar_width)

    def _apply_brand_theme(self) -> None:
        self.brand_label.configure(
            bg=self.theme["accent_soft"],
            fg=self.theme["accent"],
            font=("TkDefaultFont", 11, "bold"),
            relief="flat",
            highlightthickness=0,
        )

    def _apply_listbox_theme(self) -> None:
        for widget in (self.toc_list, self.search_list):
            widget.configure(
                bg=self.theme["surface"],
                fg=self.theme["text"],
                selectbackground=self.theme["selection"],
                selectforeground=self.theme["text"],
            )

    def _refresh_texts(self) -> None:
        self.root.title(self.tr("app_title"))
        self.brand_label.configure(text="LabNote")
        self.new_button.configure(text=self.tr("new"))
        self.open_file_button.configure(text=self.tr("open_file"))
        self.open_folder_button.configure(text=self.tr("open_folder"))
        self.save_button.configure(text=self.tr("save"))
        self.table_button.configure(text=self.tr("table_tools"))
        self.theme_label.configure(text=self.tr("theme"))
        self.language_button.configure(text=self.tr("language_toggle"))
        self.palette_button.configure(text=self.tr("command_palette"))
        self.preferences_button.configure(text=self.tr("preferences"))
        self.project_label.configure(text=self.tr("project"))
        self.sidebar_open_folder_button.configure(text=self.tr("open_folder"))
        self.toc_label.configure(text=self.tr("outline"))
        self.search_header_label.configure(text=self.tr("find_in_files"))
        self.search_button.configure(text=self.tr("search_action"))
        self.clear_search_button.configure(text=self.tr("clear"))
        self.sidebar_notebook.tab(self.file_tree_panel, text=self.tr("project"))
        self.sidebar_notebook.tab(self.toc_panel, text=self.tr("outline"))
        self.sidebar_notebook.tab(self.search_panel, text=self.tr("search"))
        self._refresh_mode_buttons()
        if self._command_palette and self._command_palette.winfo_exists():
            self._command_palette.destroy()
            self._command_palette = None

    def _refresh_mode_buttons(self) -> None:
        self.mode_editor_button.configure(text=self.i18n.mode_label("editor"), style="Accent.TButton" if self.settings.layout_mode == "editor" else "Toolbar.TButton")
        self.mode_split_button.configure(text=self.i18n.mode_label("split"), style="Accent.TButton" if self.settings.layout_mode == "split" else "Toolbar.TButton")
        self.mode_preview_button.configure(text=self.i18n.mode_label("preview"), style="Accent.TButton" if self.settings.layout_mode == "preview" else "Toolbar.TButton")

    def change_theme(self, theme_name: str) -> None:
        self.settings.theme_name = theme_name
        self.apply_settings_to_ui()
        self.show_message(self.tr("theme_switched", name=theme_name))

    def toggle_language(self) -> None:
        language = "en-US" if self.settings.language == "zh-CN" else "zh-CN"
        self.change_language(language)

    def change_language(self, language: str) -> None:
        if language not in SUPPORTED_LANGUAGES:
            return
        self.settings.language = language
        self.i18n.set_language(language)
        self.apply_settings_to_ui()
        self.show_message(self.tr("language_switched", language=self.i18n.language_label(language)))

    def _register_commands(self) -> None:
        self.command_registry.clear()
        file_category = self.tr("file")
        view_category = self.tr("view")
        tools_category = self.tr("tools")
        tab_category = self.tr("close_tab")
        commands = [
            Command("file.new", f"{file_category}: {self.tr('new')}", self.new_document, "Ctrl+N", file_category),
            Command("file.open", f"{file_category}: {self.tr('open_file')}", self.open_file_dialog, "Ctrl+O", file_category),
            Command("file.open_folder", f"{file_category}: {self.tr('open_folder')}", self.open_folder_dialog, "Ctrl+Shift+O", file_category),
            Command("file.save", f"{file_category}: {self.tr('save')}", self.save_current_document, "Ctrl+S", file_category),
            Command("file.save_as", f"{file_category}: {self.tr('save_as')}", self.save_current_document_as, "Ctrl+Shift+S", file_category),
            Command("file.reload", f"{file_category}: {self.tr('reload')}", self.reload_current_document, "", file_category),
            Command("file.export_html", f"{file_category}: {self.tr('export_html')}", self.export_current_as_html, "", file_category),
            Command("file.export_pdf", f"{file_category}: {self.tr('export_pdf')}", self.export_current_as_pdf, "", file_category),
            Command("view.sidebar", f"{view_category}: {self.tr('toggle_sidebar')}", self.toggle_sidebar, "Ctrl+\\", view_category),
            Command("view.editor", f"{view_category}: {self.i18n.mode_label('editor')}", lambda: self.set_layout_mode("editor"), "Alt+1", view_category),
            Command("view.split", f"{view_category}: {self.i18n.mode_label('split')}", lambda: self.set_layout_mode("split"), "Alt+2", view_category),
            Command("view.preview", f"{view_category}: {self.i18n.mode_label('preview')}", lambda: self.set_layout_mode("preview"), "Alt+3", view_category),
            Command("view.focus", f"{view_category}: {self.tr('toggle_focus_mode')}", self.toggle_focus_mode, "F9", view_category),
            Command("view.typewriter", f"{view_category}: {self.tr('toggle_typewriter_mode')}", self.toggle_typewriter_mode, "F10", view_category),
            Command("tools.palette", f"{tools_category}: {self.tr('command_palette')}", self.show_command_palette, "Ctrl+Shift+P", tools_category),
            Command("tools.preferences", f"{tools_category}: {self.tr('preferences')}", self.open_preferences, "Ctrl+,", tools_category),
            Command("tools.insert_table", f"{tools_category}: {self.tr('insert_table')}", self.insert_table_template, "Ctrl+Alt+T", tools_category),
            Command("tools.edit_table", f"{tools_category}: {self.tr('edit_current_table')}", self.open_table_editor, "Ctrl+Alt+E", tools_category),
            Command("tools.format_table", f"{tools_category}: {self.tr('format_current_table')}", self.format_current_table, "Ctrl+Alt+F", tools_category),
            Command("tab.close", self.tr("menu_close_current"), self.close_current_tab, "Ctrl+W", tab_category),
        ]
        for command in commands:
            self.command_registry.register(command)

    def _build_menu(self) -> None:
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)

        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label=self.tr("new"), command=self.new_document, accelerator="Ctrl+N")
        file_menu.add_command(label=self.tr("open_file"), command=self.open_file_dialog, accelerator="Ctrl+O")
        file_menu.add_command(label=self.tr("open_folder"), command=self.open_folder_dialog, accelerator="Ctrl+Shift+O")
        file_menu.add_separator()
        file_menu.add_command(label=self.tr("save"), command=self.save_current_document, accelerator="Ctrl+S")
        file_menu.add_command(label=self.tr("save_as"), command=self.save_current_document_as, accelerator="Ctrl+Shift+S")
        file_menu.add_command(label=self.tr("reload"), command=self.reload_current_document)
        file_menu.add_separator()
        file_menu.add_command(label=self.tr("export_html"), command=self.export_current_as_html)
        file_menu.add_command(label=self.tr("export_pdf"), command=self.export_current_as_pdf)
        file_menu.add_separator()
        self._recent_menu = tk.Menu(file_menu, tearoff=False)
        file_menu.add_cascade(label=self.tr("recent_files"), menu=self._recent_menu)
        self._refresh_recent_files_menu()
        file_menu.add_separator()
        file_menu.add_command(label=self.tr("menu_close_current"), command=self.close_current_tab, accelerator="Ctrl+W")
        file_menu.add_command(label=self.tr("menu_exit"), command=self.on_quit)
        menu.add_cascade(label=self.tr("file"), menu=file_menu)

        edit_menu = tk.Menu(menu, tearoff=False)
        edit_menu.add_command(label=self.tr("undo"), command=lambda: self._event_to_editor("<<Undo>>"), accelerator="Ctrl+Z")
        edit_menu.add_command(label=self.tr("redo"), command=lambda: self._event_to_editor("<<Redo>>"), accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label=self.tr("cut"), command=lambda: self._event_to_editor("<<Cut>>"), accelerator="Ctrl+X")
        edit_menu.add_command(label=self.tr("copy"), command=lambda: self._event_to_editor("<<Copy>>"), accelerator="Ctrl+C")
        edit_menu.add_command(label=self.tr("paste"), command=lambda: self._event_to_editor("<<Paste>>"), accelerator="Ctrl+V")
        edit_menu.add_command(label=self.tr("select_all"), command=lambda: self._event_to_editor("<<SelectAll>>"), accelerator="Ctrl+A")
        edit_menu.add_separator()
        edit_menu.add_command(label=self.tr("insert_table"), command=self.insert_table_template, accelerator="Ctrl+Alt+T")
        edit_menu.add_command(label=self.tr("edit_current_table"), command=self.open_table_editor, accelerator="Ctrl+Alt+E")
        edit_menu.add_command(label=self.tr("format_current_table"), command=self.format_current_table, accelerator="Ctrl+Alt+F")
        menu.add_cascade(label=self.tr("edit"), menu=edit_menu)

        view_menu = tk.Menu(menu, tearoff=False)
        view_menu.add_command(label=self.tr("toggle_sidebar"), command=self.toggle_sidebar, accelerator="Ctrl+\\")
        view_menu.add_separator()
        view_menu.add_command(label=self.i18n.mode_label("editor"), command=lambda: self.set_layout_mode("editor"), accelerator="Alt+1")
        view_menu.add_command(label=self.i18n.mode_label("split"), command=lambda: self.set_layout_mode("split"), accelerator="Alt+2")
        view_menu.add_command(label=self.i18n.mode_label("preview"), command=lambda: self.set_layout_mode("preview"), accelerator="Alt+3")
        view_menu.add_separator()
        view_menu.add_command(label=self.tr("toggle_focus_mode"), command=self.toggle_focus_mode, accelerator="F9")
        view_menu.add_command(label=self.tr("toggle_typewriter_mode"), command=self.toggle_typewriter_mode, accelerator="F10")
        menu.add_cascade(label=self.tr("view"), menu=view_menu)

        theme_menu = tk.Menu(menu, tearoff=False)
        for theme_name in THEMES:
            theme_menu.add_radiobutton(label=theme_name, value=theme_name, variable=self._theme_var, command=lambda name=theme_name: self.change_theme(name))
        menu.add_cascade(label=self.tr("theme"), menu=theme_menu)

        language_menu = tk.Menu(menu, tearoff=False)
        for language in SUPPORTED_LANGUAGES:
            language_menu.add_radiobutton(label=self.i18n.language_label(language), value=language, variable=self._language_var, command=lambda lang=language: self.change_language(lang))
        menu.add_cascade(label=self.tr("language"), menu=language_menu)

        tools_menu = tk.Menu(menu, tearoff=False)
        tools_menu.add_command(label=self.tr("command_palette"), command=self.show_command_palette, accelerator="Ctrl+Shift+P")
        tools_menu.add_command(label=self.tr("preferences"), command=self.open_preferences, accelerator="Ctrl+,")
        menu.add_cascade(label=self.tr("tools"), menu=tools_menu)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label=self.tr("about"), command=self.show_about)
        menu.add_cascade(label=self.tr("help"), menu=help_menu)

    def _refresh_recent_files_menu(self) -> None:
        if self._recent_menu is None:
            return
        self._recent_menu.delete(0, "end")
        if not self.settings.recent_files:
            self._recent_menu.add_command(label=self.tr("menu_open_recent_empty"), state="disabled")
            return
        for recent_path in self.settings.recent_files[:12]:
            self._recent_menu.add_command(label=recent_path, command=lambda path=recent_path: self.open_document_from_path(path))

    def _bind_shortcuts(self) -> None:
        bindings = {
            "<Control-n>": self.new_document,
            "<Control-o>": self.open_file_dialog,
            "<Control-s>": self.save_current_document,
            "<Control-S>": self.save_current_document,
            "<Control-w>": self.close_current_tab,
            "<Control-W>": self.close_current_tab,
            "<Control-Shift-S>": self.save_current_document_as,
            "<Control-Shift-O>": self.open_folder_dialog,
            "<Control-Shift-P>": self.show_command_palette,
            "<Control-comma>": self.open_preferences,
            "<Control-backslash>": self.toggle_sidebar,
            "<Control-Alt-t>": self.insert_table_template,
            "<Control-Alt-e>": self.open_table_editor,
            "<Control-Alt-f>": self.format_current_table,
            "<Alt-Key-1>": lambda: self.set_layout_mode("editor"),
            "<Alt-Key-2>": lambda: self.set_layout_mode("split"),
            "<Alt-Key-3>": lambda: self.set_layout_mode("preview"),
            "<F9>": self.toggle_focus_mode,
            "<F10>": self.toggle_typewriter_mode,
        }
        for sequence, callback in bindings.items():
            self.root.bind(sequence, lambda _event, cb=callback: (cb(), "break")[-1])

    def _open_startup_content(self) -> None:
        opened = False
        if self.startup_paths:
            for raw_path in self.startup_paths:
                path = Path(raw_path)
                if path.is_dir():
                    self.open_folder(path)
                elif path.is_file():
                    self.open_document_from_path(path)
                    opened = True
        elif self.settings.restore_session and self.settings.session_files:
            for raw_path in self.settings.session_files:
                if Path(raw_path).is_file():
                    self.open_document_from_path(raw_path)
                    opened = True
            if self.settings.last_folder and Path(self.settings.last_folder).is_dir():
                self.open_folder(Path(self.settings.last_folder))
            if self.settings.session_active and Path(self.settings.session_active).is_file():
                document = self.document_manager.find_by_path(Path(self.settings.session_active))
                if document:
                    self.select_document(document.id)
        elif self.settings.last_folder and Path(self.settings.last_folder).is_dir():
            self.open_folder(Path(self.settings.last_folder))

        if not self.views:
            self.new_document()
        if not opened:
            self.show_message(self.tr("ready"))

    def _new_untitled_title(self) -> str:
        current_untitled = sum(1 for document in self.document_manager.all_documents() if document.path is None) + 1
        return self.tr("untitled_number", index=current_untitled)

    def new_document(self) -> None:
        document = self.document_manager.new_document(title=self._new_untitled_title())
        self._create_document_view(document)
        self.show_message(self.tr("new_tab_created"))

    def open_file_dialog(self) -> None:
        file_paths = filedialog.askopenfilenames(title=self.tr("open_file"), filetypes=MARKDOWN_FILETYPES)
        if not file_paths:
            return
        for file_path in file_paths:
            self.open_document_from_path(file_path)

    def open_document_from_path(self, path: str | Path) -> None:
        try:
            document = self.document_manager.open_file(path)
        except OSError as exc:
            messagebox.showerror(self.tr("open_file_failed"), str(exc), parent=self.root)
            return
        if document.id in self.views:
            self.select_document(document.id)
        else:
            self._create_document_view(document)
        if document.path:
            self._remember_recent_file(document.path)
            self.file_watcher.watch(document.path)
            self.path_var.set(str(document.path))
        self.show_message(self.tr("opened_file", name=document.display_name))

    def _create_document_view(self, document: DocumentState) -> None:
        view = DocumentView(
            self.view_stack,
            document=document,
            engine=self.engine,
            on_content_changed=self._on_document_content_changed,
            on_rendered=self._on_document_rendered,
            on_status_update=self._update_stats,
            on_split_ratio_changed=self._on_editor_split_ratio_changed,
        )
        view.grid(row=0, column=0, sticky="nsew")
        self.views[document.id] = view
        self.view_order.append(document.id)
        self.tabbar.add_tab(document.id, self._tab_title(document))
        view.set_theme(self.settings.theme_name or DEFAULT_THEME, self.theme, font_size=self.settings.font_size, code_font_size=self.settings.code_font_size, line_spacing=self.settings.line_spacing)
        view.set_layout_mode(self.settings.layout_mode)
        view.set_typewriter_mode(self.settings.typewriter_mode)
        view.set_split_ratio(self.settings.editor_split_ratio)
        if document.path:
            self.file_watcher.watch(document.path)
        self.select_document(document.id)

    def current_view(self) -> DocumentView | None:
        if self.active_document_id is None:
            return None
        return self.views.get(self.active_document_id)

    def current_document(self) -> DocumentState | None:
        view = self.current_view()
        return view.document if view else None

    def select_document(self, document_id: str) -> None:
        if document_id not in self.views:
            return
        previous = self.current_view()
        if previous and previous.document.id != document_id:
            previous.grid_remove()
        view = self.views[document_id]
        view.grid()
        view.tkraise()
        self.active_document_id = document_id
        self.document_manager.set_active(document_id)
        self.tabbar.select(document_id)
        self._refresh_status_for_current_tab()
        view.focus_editor()

    def save_current_document(self) -> None:
        document = self.current_document()
        if document:
            self._save_document(document)

    def save_current_document_as(self) -> None:
        document = self.current_document()
        if document:
            self._save_document(document, force_dialog=True)

    def _save_document(self, document: DocumentState, force_dialog: bool = False) -> bool:
        target_path: str | None = None
        if force_dialog or not document.path:
            suggested = document.path.name if document.path else f"{document.title}.md"
            target_path = filedialog.asksaveasfilename(title=self.tr("save"), defaultextension=".md", initialfile=suggested, filetypes=MARKDOWN_FILETYPES)
            if not target_path:
                return False
        view = self.views.get(document.id)
        if view:
            document.content = view.get_content()
        try:
            self.document_manager.save_document(document, target_path=target_path)
        except OSError as exc:
            messagebox.showerror(self.tr("save_failed"), str(exc), parent=self.root)
            return False
        self._update_tab_title(document)
        if document.path:
            self._remember_recent_file(document.path)
            self.file_watcher.watch(document.path)
            self.path_var.set(str(document.path))
        self.show_message(self.tr("saved_file", name=document.display_name))
        return True

    def reload_current_document(self) -> None:
        document = self.current_document()
        if not document or not document.path:
            return
        if document.dirty:
            answer = messagebox.askyesno(self.tr("confirm_reload_title"), self.tr("confirm_reload_body", name=document.display_name), parent=self.root)
            if not answer:
                return
        try:
            self.document_manager.reload_from_disk(document)
        except OSError as exc:
            messagebox.showerror(self.tr("reload_failed"), str(exc), parent=self.root)
            return
        view = self.views.get(document.id)
        if view:
            view.set_content(document.content)
        self._update_tab_title(document)
        self.show_message(self.tr("reloaded_file", name=document.display_name))

    def close_current_tab(self) -> None:
        if self.active_document_id:
            self.close_document_by_id(self.active_document_id)

    def close_document_by_id(self, document_id: str) -> None:
        document = self.document_manager.get(document_id)
        view = self.views.get(document_id)
        if not document or not view:
            return
        if not self._confirm_close_document(document):
            return
        if document.path:
            self.file_watcher.unwatch(document.path)
        next_active = self._next_document_id_after_closing(document_id)
        view.destroy()
        self.views.pop(document_id, None)
        self.rendered_cache.pop(document_id, None)
        self.tabbar.remove_tab(document_id)
        if document_id in self.view_order:
            self.view_order.remove(document_id)
        self.document_manager.close_document(document_id)
        job = self._auto_save_jobs.pop(document_id, None)
        if job:
            self.root.after_cancel(job)
        self.show_message(self.tr("closed_file", name=document.display_name))
        if not self.views:
            self.active_document_id = None
            self.new_document()
        else:
            self.select_document(next_active)

    def _next_document_id_after_closing(self, document_id: str) -> str:
        if document_id not in self.view_order:
            return self.view_order[0]
        index = self.view_order.index(document_id)
        if index + 1 < len(self.view_order):
            return self.view_order[index + 1]
        if index - 1 >= 0:
            return self.view_order[index - 1]
        return self.view_order[0]

    def _confirm_close_document(self, document: DocumentState) -> bool:
        if not document.dirty:
            return True
        answer = messagebox.askyesnocancel(self.tr("confirm_unsaved_title"), self.tr("confirm_unsaved_body", name=document.display_name), parent=self.root)
        if answer is None:
            return False
        if answer:
            return self._save_document(document)
        return True

    def _tab_title(self, document: DocumentState) -> str:
        return f"• {document.display_name}" if document.dirty else document.display_name

    def _update_tab_title(self, document: DocumentState) -> None:
        self.tabbar.update_title(document.id, self._tab_title(document))

    def _on_document_content_changed(self, document: DocumentState) -> None:
        self._update_tab_title(document)
        self._schedule_auto_save(document)
        self._refresh_status_for_current_tab()

    def _on_document_rendered(self, document: DocumentState, rendered: RenderedMarkdown) -> None:
        self.rendered_cache[document.id] = rendered
        current = self.current_document()
        if current and current.id == document.id:
            self._refresh_toc(rendered)
            self._refresh_status_for_current_tab()

    def _refresh_toc(self, rendered: RenderedMarkdown | None) -> None:
        self.toc_list.delete(0, "end")
        if not rendered:
            return
        for heading in rendered.toc:
            indent = "  " * max(0, heading.level - 1)
            self.toc_list.insert("end", f"{indent}{heading.text}")

    def _jump_to_selected_heading(self, _event: tk.Event | None = None) -> None:
        view = self.current_view()
        document = self.current_document()
        if not view or not document:
            return
        selection = self.toc_list.curselection()
        if not selection:
            return
        rendered = self.rendered_cache.get(document.id)
        if not rendered or selection[0] >= len(rendered.toc):
            return
        heading = rendered.toc[selection[0]]
        view.go_to_line(heading.line_number)
        self.show_message(self.tr("jumped_heading", name=heading.text))

    def _refresh_status_for_current_tab(self) -> None:
        document = self.current_document()
        view = self.current_view()
        if document and view:
            self.path_var.set(document.full_display_name)
            self.stats_var.set(self.tr("stats", **view.stats_payload()))
            self.document_manager.set_active(document.id)
            self._refresh_toc(self.rendered_cache.get(document.id))
        else:
            self.path_var.set("")
            self.stats_var.set("")
            self._refresh_toc(None)

    def _update_stats(self, stats_payload: StatsPayload) -> None:
        self.stats_var.set(self.tr("stats", **stats_payload))

    def open_folder_dialog(self) -> None:
        initial = self.current_folder or (Path(self.settings.last_folder) if self.settings.last_folder else Path.home())
        folder = filedialog.askdirectory(title=self.tr("open_folder"), initialdir=str(initial))
        if folder:
            self.open_folder(Path(folder))

    def open_folder(self, folder: Path) -> None:
        self.current_folder = folder.resolve()
        self.settings.last_folder = str(self.current_folder)
        self._populate_file_tree()
        self.show_message(self.tr("opened_folder", path=str(self.current_folder)))

    def _populate_file_tree(self) -> None:
        self.file_tree.delete(*self.file_tree.get_children())
        if not self.current_folder or not self.current_folder.exists():
            return
        root_id = str(self.current_folder)
        self.file_tree.insert("", "end", iid=root_id, text=self.current_folder.name or str(self.current_folder), open=True)
        self._insert_tree_children(root_id, self.current_folder)

    def _insert_tree_children(self, parent_id: str, folder: Path) -> None:
        try:
            children = sorted(folder.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
        except OSError:
            return
        for child in children:
            if child.name.startswith(".") and child.name not in {".github"}:
                continue
            if child.is_dir() and child.name in {"node_modules", "dist", "build", "__pycache__", ".venv", "venv"}:
                continue
            child_id = str(child)
            self.file_tree.insert(parent_id, "end", iid=child_id, text=child.name, open=False)
            if child.is_dir():
                self._insert_tree_children(child_id, child)

    def _open_selected_tree_item(self, _event: tk.Event | None = None) -> None:
        selection = self.file_tree.selection()
        if not selection:
            return
        path = Path(selection[0])
        if path.is_file():
            self.open_document_from_path(path)

    def perform_search(self) -> None:
        if not self.current_folder:
            messagebox.showinfo(self.tr("search_folder_first_title"), self.tr("search_folder_first_body"), parent=self.root)
            return
        query = self.search_var.get().strip()
        if not query:
            return
        self.search_results = self.searcher.search(self.current_folder, query)
        self.search_list.delete(0, "end")
        self._search_results_meta.clear()
        for index, match in enumerate(self.search_results):
            relative = match.file_path.relative_to(self.current_folder) if self.current_folder in match.file_path.parents or match.file_path == self.current_folder else match.file_path
            line = self.tr("search_result_line", path=relative, line=match.line_number, text=match.line_text.strip())
            self.search_list.insert("end", line)
            self._search_results_meta[index] = match
        self.sidebar_notebook.select(self.search_panel)
        self.show_message(self.tr("search_finished", count=len(self.search_results)))

    def clear_search_results(self) -> None:
        self.search_list.delete(0, "end")
        self._search_results_meta.clear()
        self.search_results = []
        self.show_message(self.tr("search_cleared"))

    def _open_selected_search_result(self, _event: tk.Event | None = None) -> None:
        selection = self.search_list.curselection()
        if not selection:
            return
        match = self._search_results_meta.get(selection[0])
        if not match:
            return
        self.open_document_from_path(match.file_path)
        view = self.current_view()
        if view:
            view.go_to_line(match.line_number)
        self.show_message(self.tr("opened_search_match", name=match.file_path.name, line=match.line_number))

    def export_current_as_html(self) -> None:
        document = self.current_document()
        view = self.current_view()
        if not document or not view:
            return
        suggested = (document.path.stem if document.path else document.title) + ".html"
        target_path = filedialog.asksaveasfilename(title=self.tr("export_html"), defaultextension=".html", initialfile=suggested, filetypes=[("HTML", "*.html")])
        if not target_path:
            return
        try:
            self.export_service.export_html(view.get_content(), target_path, theme_name=self.settings.theme_name, title=document.display_name)
        except OSError as exc:
            messagebox.showerror(self.tr("export_html_failed"), str(exc), parent=self.root)
            return
        self.show_message(f"HTML → {target_path}")

    def export_current_as_pdf(self) -> None:
        document = self.current_document()
        view = self.current_view()
        if not document or not view:
            return
        suggested = (document.path.stem if document.path else document.title) + ".pdf"
        target_path = filedialog.asksaveasfilename(title=self.tr("export_pdf"), defaultextension=".pdf", initialfile=suggested, filetypes=[("PDF", "*.pdf")])
        if not target_path:
            return
        try:
            self.export_service.export_pdf(view.get_content(), target_path, title=document.display_name)
        except OSError as exc:
            messagebox.showerror(self.tr("export_pdf_failed"), str(exc), parent=self.root)
            return
        self.show_message(f"PDF → {target_path}")

    def set_layout_mode(self, mode: str) -> None:
        self.settings.layout_mode = mode
        for view in self.views.values():
            view.set_layout_mode(mode)
        self._refresh_mode_buttons()
        self.show_message(self.tr("layout_switched", mode=self.i18n.mode_label(mode)))

    def toggle_sidebar(self) -> None:
        self.settings.show_sidebar = not self.settings.show_sidebar
        self._apply_sidebar_visibility()
        self.show_message(self.tr("sidebar_shown") if self.settings.show_sidebar else self.tr("sidebar_hidden"))

    def toggle_focus_mode(self) -> None:
        self.settings.focus_mode = not self.settings.focus_mode
        self._apply_focus_mode()
        self.show_message(self.tr("focus_mode_on") if self.settings.focus_mode else self.tr("focus_mode_off"))

    def toggle_typewriter_mode(self) -> None:
        self.settings.typewriter_mode = not self.settings.typewriter_mode
        for view in self.views.values():
            view.set_typewriter_mode(self.settings.typewriter_mode)
        self.show_message(self.tr("typewriter_mode_on") if self.settings.typewriter_mode else self.tr("typewriter_mode_off"))

    def insert_table_template(self) -> None:
        view = self.current_view()
        if not view:
            return
        view.insert_table_template()
        self.show_message(self.tr("table_inserted"))

    def open_table_editor(self) -> None:
        view = self.current_view()
        if not view:
            return
        table = view.find_current_table()
        if not table:
            messagebox.showinfo(self.tr("table_tools"), self.tr("table_not_found"), parent=self.root)
            return
        result = show_table_editor(self.root, table, self.i18n)
        if result is None:
            return
        if view.replace_current_table(result):
            self.show_message(self.tr("table_updated"))

    def format_current_table(self) -> None:
        view = self.current_view()
        if not view:
            return
        if not view.format_current_table():
            messagebox.showinfo(self.tr("table_tools"), self.tr("table_not_found"), parent=self.root)
            return
        self.show_message(self.tr("table_formatted"))

    def show_command_palette(self) -> None:
        if self._command_palette and self._command_palette.winfo_exists():
            self._command_palette.open()
            return
        self._command_palette = CommandPalette(self.root, self.command_registry, self.i18n)
        self._command_palette.open()

    def open_preferences(self) -> None:
        result = show_preferences(self.root, self.settings, list(THEMES.keys()), self.i18n)
        if result is None:
            return
        result.recent_files = self.settings.recent_files
        result.last_folder = self.settings.last_folder
        result.window_width = self.settings.window_width
        result.window_height = self.settings.window_height
        result.sidebar_width = self.settings.sidebar_width
        result.editor_split_ratio = self.settings.editor_split_ratio
        result.session_files = self.settings.session_files
        result.session_active = self.settings.session_active
        self.settings = result
        self.apply_settings_to_ui()
        self.show_message(self.tr("preferences_saved"))

    def show_about(self) -> None:
        messagebox.showinfo(self.tr("about"), self.tr("about_body"), parent=self.root)

    def _event_to_editor(self, sequence: str) -> None:
        view = self.current_view()
        if view:
            view.editor.event_generate(sequence)
            view.focus_editor()

    def _schedule_auto_save(self, document: DocumentState) -> None:
        if not self.settings.auto_save or not document.path:
            return
        existing = self._auto_save_jobs.pop(document.id, None)
        if existing:
            self.root.after_cancel(existing)
        job = self.root.after(self.settings.auto_save_delay_ms, lambda doc_id=document.id: self._auto_save_document(doc_id))
        self._auto_save_jobs[document.id] = job

    def _auto_save_document(self, document_id: str) -> None:
        self._auto_save_jobs.pop(document_id, None)
        document = self.document_manager.get(document_id)
        if not document or not document.path or not document.dirty:
            return
        self._save_document(document)

    def _notify_external_change(self, path: Path) -> None:
        self.root.after(0, lambda changed_path=path: self._handle_external_change(changed_path))

    def _handle_external_change(self, path: Path) -> None:
        document = self.document_manager.find_by_path(path)
        if not document:
            return
        if document.dirty:
            self.show_message(self.tr("external_changed", name=document.display_name))
            return
        try:
            self.document_manager.reload_from_disk(document)
        except OSError:
            return
        view = self.views.get(document.id)
        if view:
            view.set_content(document.content)
        self._update_tab_title(document)
        self.show_message(self.tr("external_reloaded", name=document.display_name))

    def _apply_sidebar_visibility(self) -> None:
        should_show = self.settings.show_sidebar and not self.settings.focus_mode
        panes = list(self.body_paned.panes())
        sidebar_name = str(self.sidebar)
        if should_show and sidebar_name not in panes:
            self.body_paned.insert(0, self.sidebar, weight=0)
            self.root.after(80, self._apply_sidebar_width)
        elif not should_show and sidebar_name in panes:
            self.body_paned.forget(self.sidebar)

    def _apply_sidebar_width(self) -> None:
        if str(self.sidebar) not in self.body_paned.panes():
            return
        width = self.body_paned.winfo_width()
        if width <= 12:
            self.root.after(80, self._apply_sidebar_width)
            return
        sidebar_width = max(220, min(self.settings.sidebar_width, max(260, width - 420)))
        self.body_paned.sashpos(0, sidebar_width)

    def _apply_focus_mode(self) -> None:
        if self.settings.focus_mode:
            self.status.grid_remove()
        else:
            self.status.grid(row=2, column=0, sticky="ew")
        self._apply_sidebar_visibility()

    def _remember_sidebar_width(self, _event: tk.Event | None = None) -> None:
        if str(self.sidebar) not in self.body_paned.panes():
            return
        self.settings.sidebar_width = self.body_paned.sashpos(0)

    def _on_editor_split_ratio_changed(self, ratio: float) -> None:
        self.settings.editor_split_ratio = ratio

    def show_message(self, text: str) -> None:
        self.message_var.set(text)
        if self._message_job:
            self.root.after_cancel(self._message_job)
        self._message_job = self.root.after(5000, lambda: self.message_var.set(self.tr("ready")))

    def _remember_recent_file(self, path: Path) -> None:
        normalized = str(path.resolve())
        recent = [entry for entry in self.settings.recent_files if entry != normalized]
        recent.insert(0, normalized)
        self.settings.recent_files = recent[:15]
        self._refresh_recent_files_menu()

    def on_quit(self) -> None:
        for document_id in list(self.views.keys()):
            document = self.document_manager.get(document_id)
            if document and not self._confirm_close_document(document):
                return
        self._persist_session()
        self.file_watcher.stop()
        self.root.destroy()

    def _persist_session(self) -> None:
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if width > 0:
            self.settings.window_width = width
        if height > 0:
            self.settings.window_height = height
        self.settings.session_files = [str(document.path) for document in self.document_manager.all_documents() if document.path]
        current = self.current_document()
        self.settings.session_active = str(current.path) if current and current.path else ""
        self.settings_store.save(self.settings)
