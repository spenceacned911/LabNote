from __future__ import annotations

import argparse
import sys
import tkinter as tk
from pathlib import Path

from labnote import __version__
from labnote.app.settings import SettingsStore
from labnote.ui.main_window import MainWindow


class LabNoteApplication:
    def __init__(self, startup_paths: list[str] | None = None) -> None:
        self.startup_paths = startup_paths or []
        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()

    def run(self) -> None:
        root = tk.Tk()
        MainWindow(root=root, settings_store=self.settings_store, settings=self.settings, startup_paths=self.startup_paths)
        root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LabNote")
    parser.add_argument("paths", nargs="*", help="Markdown files or folders to open")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    startup_paths = [str(Path(item).expanduser()) for item in args.paths]
    app = LabNoteApplication(startup_paths=startup_paths)
    app.run()


if __name__ == "__main__":
    main(sys.argv[1:])
