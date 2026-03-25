from __future__ import annotations

from copy import deepcopy
import tkinter as tk
from tkinter import ttk


THEMES: dict[str, dict[str, str]] = {
    "Pearl Light": {
        "mode": "light",
        "window_bg": "#f4f7fb",
        "toolbar_bg": "#f5f7fb",
        "surface": "#ffffff",
        "surface_alt": "#eef3f9",
        "surface_deep": "#e4ebf5",
        "sidebar_bg": "#f8fbff",
        "editor_bg": "#fefeff",
        "preview_bg": "#fbfcfe",
        "tab_active_bg": "#ffffff",
        "tab_inactive_bg": "#edf2f9",
        "tab_hover_bg": "#e7edf8",
        "status_bg": "#eef3f8",
        "text": "#162033",
        "text_soft": "#607089",
        "text_muted": "#7a8699",
        "accent": "#2962ff",
        "accent_hover": "#1f54e7",
        "accent_soft": "#dce7ff",
        "selection": "#d7e5ff",
        "border": "#d7dfeb",
        "border_strong": "#bec9d8",
        "editor_line": "#f0f4fa",
        "code_bg": "#f2f6fb",
        "quote_bg": "#eef4ff",
        "link": "#245cff",
        "danger": "#df4f57",
        "success": "#2f9e44",
    },
    "Slate Light": {
        "mode": "light",
        "window_bg": "#f1f4f8",
        "toolbar_bg": "#eff3f8",
        "surface": "#ffffff",
        "surface_alt": "#edf1f6",
        "surface_deep": "#e1e6ee",
        "sidebar_bg": "#f6f8fb",
        "editor_bg": "#ffffff",
        "preview_bg": "#fafbfd",
        "tab_active_bg": "#ffffff",
        "tab_inactive_bg": "#edf1f6",
        "tab_hover_bg": "#e8edf4",
        "status_bg": "#ebeff5",
        "text": "#1b2430",
        "text_soft": "#5f6b7a",
        "text_muted": "#7c8795",
        "accent": "#0f62fe",
        "accent_hover": "#0a53da",
        "accent_soft": "#dce7ff",
        "selection": "#d8e5ff",
        "border": "#d3dae5",
        "border_strong": "#b9c3d1",
        "editor_line": "#f1f4f8",
        "code_bg": "#eef2f8",
        "quote_bg": "#edf4ff",
        "link": "#0f62fe",
        "danger": "#d9485c",
        "success": "#2f9e44",
    },
    "Graphite Dark": {
        "mode": "dark",
        "window_bg": "#11161f",
        "toolbar_bg": "#141a24",
        "surface": "#171e2a",
        "surface_alt": "#1d2634",
        "surface_deep": "#243041",
        "sidebar_bg": "#141a24",
        "editor_bg": "#111823",
        "preview_bg": "#131b27",
        "tab_active_bg": "#1c2534",
        "tab_inactive_bg": "#141c28",
        "tab_hover_bg": "#202a3a",
        "status_bg": "#141b25",
        "text": "#ebf0f8",
        "text_soft": "#a9b6c8",
        "text_muted": "#8f9caf",
        "accent": "#7aa2ff",
        "accent_hover": "#628cf4",
        "accent_soft": "#1e2b44",
        "selection": "#2a4272",
        "border": "#2b3445",
        "border_strong": "#3a465a",
        "editor_line": "#182130",
        "code_bg": "#0d131b",
        "quote_bg": "#1a2536",
        "link": "#89adff",
        "danger": "#ff6b6b",
        "success": "#55c97a",
    },
    "Midnight": {
        "mode": "dark",
        "window_bg": "#0d1118",
        "toolbar_bg": "#101722",
        "surface": "#141c29",
        "surface_alt": "#1a2332",
        "surface_deep": "#243043",
        "sidebar_bg": "#101722",
        "editor_bg": "#0f1622",
        "preview_bg": "#111927",
        "tab_active_bg": "#192436",
        "tab_inactive_bg": "#101722",
        "tab_hover_bg": "#1e2940",
        "status_bg": "#101722",
        "text": "#edf3fb",
        "text_soft": "#b4c0d0",
        "text_muted": "#92a0b2",
        "accent": "#79c0ff",
        "accent_hover": "#5fb5ff",
        "accent_soft": "#1a2a3d",
        "selection": "#27405f",
        "border": "#263143",
        "border_strong": "#36455c",
        "editor_line": "#152030",
        "code_bg": "#0b1119",
        "quote_bg": "#162131",
        "link": "#7dc6ff",
        "danger": "#ff7b72",
        "success": "#56d364",
    },
}

DEFAULT_THEME = "Graphite Dark"


def get_theme(name: str | None) -> dict[str, str]:
    if not name:
        return deepcopy(THEMES[DEFAULT_THEME])
    return deepcopy(THEMES.get(name, THEMES[DEFAULT_THEME]))


def apply_theme(root: tk.Misc, theme_name: str) -> dict[str, str]:
    theme = get_theme(theme_name)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=theme["window_bg"])

    style.configure(".", background=theme["window_bg"], foreground=theme["text"], fieldbackground=theme["surface"], bordercolor=theme["border"])
    style.configure("TFrame", background=theme["window_bg"])
    style.configure("Surface.TFrame", background=theme["surface"])
    style.configure("Toolbar.TFrame", background=theme["toolbar_bg"])
    style.configure("Sidebar.TFrame", background=theme["sidebar_bg"])
    style.configure("Status.TFrame", background=theme["status_bg"])
    style.configure("Card.TFrame", background=theme["surface"])
    style.configure("TabBar.TFrame", background=theme["toolbar_bg"])

    style.configure("TLabel", background=theme["window_bg"], foreground=theme["text"])
    style.configure("Surface.TLabel", background=theme["surface"], foreground=theme["text"])
    style.configure("Sidebar.TLabel", background=theme["sidebar_bg"], foreground=theme["text"])
    style.configure("Muted.TLabel", background=theme["window_bg"], foreground=theme["text_soft"])
    style.configure("Toolbar.TLabel", background=theme["toolbar_bg"], foreground=theme["text_soft"])
    style.configure("Status.TLabel", background=theme["status_bg"], foreground=theme["text_soft"])
    style.configure("Heading.TLabel", background=theme["window_bg"], foreground=theme["text"], font=("TkDefaultFont", 10, "bold"))

    style.configure("TButton", background=theme["surface_alt"], foreground=theme["text"], bordercolor=theme["border"], focusthickness=0, focuscolor=theme["accent_soft"], padding=(12, 8))
    style.map("TButton", background=[("active", theme["surface"]), ("pressed", theme["surface_deep"])] )
    style.configure("Accent.TButton", background=theme["accent"], foreground="#ffffff", bordercolor=theme["accent"], padding=(12, 8))
    style.map("Accent.TButton", background=[("active", theme["accent_hover"]), ("pressed", theme["accent_hover"])] )
    style.configure("Toolbar.TButton", background=theme["surface_alt"], foreground=theme["text"], bordercolor=theme["border"], padding=(12, 8))
    style.map("Toolbar.TButton", background=[("active", theme["surface"]), ("pressed", theme["surface_deep"])] )
    style.configure("Ghost.TButton", background=theme["toolbar_bg"], foreground=theme["text_soft"], bordercolor=theme["toolbar_bg"], padding=(10, 8))
    style.map("Ghost.TButton", background=[("active", theme["surface_alt"]), ("pressed", theme["surface_alt"])] )

    style.configure("TCheckbutton", background=theme["window_bg"], foreground=theme["text"])
    style.configure("TRadiobutton", background=theme["window_bg"], foreground=theme["text"])
    style.configure("TSpinbox", arrowsize=14)
    style.configure("TEntry", fieldbackground=theme["surface"], foreground=theme["text"], insertcolor=theme["text"], bordercolor=theme["border"], padding=8)
    style.map("TEntry", fieldbackground=[("focus", theme["surface"])] )
    style.configure("TCombobox", fieldbackground=theme["surface"], foreground=theme["text"], selectbackground=theme["selection"], selectforeground=theme["text"], bordercolor=theme["border"], arrowsize=14, padding=6)
    style.map("TCombobox", fieldbackground=[("readonly", theme["surface"])] )

    style.configure("TNotebook", background=theme["sidebar_bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=theme["surface_alt"], foreground=theme["text_soft"], padding=(14, 8), borderwidth=0)
    style.map("TNotebook.Tab", background=[("selected", theme["surface"]), ("active", theme["surface"])] , foreground=[("selected", theme["text"]), ("active", theme["text"])] )

    style.configure("Treeview", background=theme["surface"], foreground=theme["text"], fieldbackground=theme["surface"], bordercolor=theme["border"], rowheight=26)
    style.configure("Treeview.Heading", background=theme["surface_alt"], foreground=theme["text"], relief="flat")
    style.map("Treeview", background=[("selected", theme["selection"])], foreground=[("selected", theme["text"])] )

    style.configure("Vertical.TScrollbar", background=theme["surface_alt"], troughcolor=theme["surface"], bordercolor=theme["border"], arrowcolor=theme["text"])
    style.configure("Horizontal.TScrollbar", background=theme["surface_alt"], troughcolor=theme["surface"], bordercolor=theme["border"], arrowcolor=theme["text"])
    style.configure("Sash", sashthickness=8)

    return theme
