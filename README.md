# LabNote

We have built **LabNote** into a local-first, bilingual-friendly, well-structured, and long-term maintainable Markdown desktop editor.

It originally started as a Python rewrite experiment based on the **architectural concepts of MarkText**. However, it is no longer just a "rewrite demo." We have thoroughly polished its branding, UI, interactions, table tools, Chinese PDF export, project documentation, and testing suite, transforming it into a standalone project that we are committed to actively maintaining.

---
## 📦 Download

The packaged **Windows and macOS versions** are available for download on the Releases page:

👉 https://github.com/jinpengaaaaa-ctrl/LabNote/releases
---

## Project Positioning

Instead of translating the original Electron / Vue project line-by-line into Python, we leveraged its core layered architecture and reorganized it into a Python implementation better suited for long-term desktop maintenance.

We envision LabNote with the following traits:

- A smooth and hassle-free Markdown writing experience
- A clean, modern, and professional aesthetic
- A clear structure, facilitating continuous iteration
- Stabilizing core experiences first, then gradually adding advanced capabilities

In other words, LabNote is not a thrown-together "as long as it runs" shell, but a robust desktop application skeleton capable of supporting future evolution.

---

## Key Features Implemented

### 1. UI / UX Refactoring

We reorganized the visual and interactive rhythm of the entire interface. The goal is not to "pile up features," but to "make high-frequency operations feel natural."

This version currently features:

- A minimalist, modern, and professional main interface style
- A Dark / Light theme system
- Clear visual hierarchy: Window, Sidebar, Tab bar, Editor, Previewer, and Status bar are distinctly separated
- Prominent mode switching at the top: **Editor Only / Split View / Preview Only**
- Left sidebar supporting **Project / Outline / Search**
- Draggable split view between the sidebar and the main area
- Draggable split view between the editor and the previewer
- Multi-tab support with explicit `×` close buttons

### 2. Core Editing Capabilities

- Multi-tab Markdown editing
- New / Open / Save / Save As / Reload from disk
- Active line highlight
- Auto-save
- Recent files
- Session restoration
- Command Palette
- Focus Mode
- Typewriter Mode
- In-project full-text search
- Table of Contents (TOC)
- One-click Chinese/English UI toggle

### 3. Markdown Preview & Export

- Real-time preview
- HTML export
- PDF export
- Common Markdown syntax support:
  - Headers
  - Paragraphs
  - Emphasis / Bold / Strikethrough
  - Inline code / Code blocks
  - Lists / Task lists
  - Blockquotes
  - Tables
  - Links
  - Footnotes (basic rendering)

### 4. Table Enhancements

We extracted and completely rebuilt the table-related logic, rather than just treating tables as plain text to make do.

It now supports:

- Parsing Markdown tables
- Formatting the current table
- Inserting table templates
- Editing the table at the cursor position
- Adding/removing rows, adding/removing columns, modifying headers, modifying cells
- Automatically adjusting column widths
- Handling East Asian Width for mixed Chinese-English text to minimize misalignment
- The previewer renders tables using actual grids instead of stuffing them back into a plain text block

Default shortcuts:

- `Ctrl + Alt + T`: Insert table template
- `Ctrl + Alt + E`: Edit current table
- `Ctrl + Alt + F`: Format current table

---

## Tech Stack

### UI / Desktop Layer
- **Tkinter / ttk**: Desktop main interface, multi-tabs, menus, sidebar, status bar, dialogs

### Markdown Core Layer
- **mistune**: Markdown parsing and AST building
- **Pygments**: Code highlighting
- **ReportLab**: PDF export

### Infrastructure
- `pathlib`: Path management
- `threading`: Polling-based file watcher
- `json`: Settings persistence
- `argparse`: CLI entry point

We chose this combination not to chase "buzzwords," but because it is lightweight, stable, and easy to build upon.

---

## Architecture Design

We continued the core layered philosophy of the original MarkText, dividing the project into three layers:

1. **Application / Controller Layer**  
   Manages windows, commands, settings, file I/O, and file change watching.

2. **Core / Editor Capability Layer**  
   Handles Markdown parsing, TOC extraction, exporting, project search, and table processing.

3. **UI / Rendering Layer**  
   Responsible for the desktop interface, multi-tabs, sidebar, real-time preview, command palette, and theme system.

### Mapping to the Original Architecture

| Original Layer | Original Project Responsibilities | LabNote Equivalent |
| -------------- | ------------------------------------------- | --------------- |
| `src/main`     | Application entry, window, file I/O, settings, commands, shortcuts | `labnote/app/`  |
| `src/muya`     | Markdown core, document transformation, export | `labnote/core/` |
| `src/renderer` | Editor UI, sidebar, tabs, interactions | `labnote/ui/`   |

### Current Directory Structure

```text
labnote/
├── app/
│   ├── application.py      # Application entry and lifecycle
│   ├── commands.py         # Command registry
│   ├── document_manager.py # Document opening, saving, reloading
│   ├── file_watcher.py     # External file polling watcher
│   ├── i18n.py             # Chinese/English localization
│   └── settings.py         # Configuration persistence
│
├── core/
│   ├── document.py         # Document state object
│   ├── markdown_engine.py  # Markdown -> AST / HTML / TOC
│   ├── exporters.py        # HTML / PDF export
│   ├── search.py           # Project search
│   ├── tables.py           # Markdown table parsing and formatting
│   └── toc.py              # Document TOC extraction
│
└── ui/
    ├── main_window.py      # Main window and interaction orchestration
    ├── document_view.py    # Single document edit / preview view
    ├── preview_renderer.py # AST -> Tk preview rendering
    ├── dialogs.py          # Command palette / Preferences / Table tools
    ├── themes.py           # Theme system
    └── widgets.py          # Closable tab bar and other custom widgets
```



## Running Guide

### Requirements

- Python **3.10+**
- Windows / macOS / Linux
- Tkinter is generally provided with the official Python distribution

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Directly

``` bash
python run.py
```

### Run as a Module

```bash
python -m labnote
```

### Open a File or Directory on Startup

```bash
python -m labnote demo/example.md
python -m labnote README.md ./demo
```



## Usage

### Sidebar

* **Project**: Browse project file tree
* **Outline**: Browse and jump to current document TOC
* **Search**: Perform full-text search within the current project

### Tabs

- Each tab has a clearly clickable `×` on the right side
- Unsaved documents will display a dirty state indicator

### Preferences

Currently supported configurations:

- Theme
- UI Language
- Body Font Size
- Code Font Size
- Line Height
- Default Layout
- Auto-save
- Session Restoration
- Default Sidebar Visibility
- Default Focus Mode
- Default Typewriter Mode

### Shortcuts

| Function | Shortcut |
| --------------- | -------------- |
| New Tab | `Ctrl+N` |
| Open File | `Ctrl+O` |
| Open Folder | `Ctrl+Shift+O` |
| Save | `Ctrl+S` |
| Save As | `Ctrl+Shift+S` |
| Close Tab | `Ctrl+W` |
| Command Palette | `Ctrl+Shift+P` |
| Preferences | `Ctrl+,` |
| Toggle Sidebar | `Ctrl+\` |
| Editor Only | `Alt+1` |
| Split | `Alt+2` |
| Preview Only | `Alt+3` |
| Focus Mode | `F9` |
| Typewriter Mode | `F10` |
| Insert Table Template | `Ctrl+Alt+T` |
| Edit Current Table | `Ctrl+Alt+E` |
| Format Current Table | `Ctrl+Alt+F` |

### Configuration File Path

Configuration directories are uniformly placed under the `labnote` namespace:

- Linux: `~/.config/labnote/settings.json`
- macOS: `~/Library/Application Support/labnote/settings.json`
- Windows: `%APPDATA%/labnote/settings.json`

Configuration contents include:

- Theme
- UI Language
- Font Size
- Auto-save
- Session Restoration
- Sidebar State
- Layout Mode
- Focus Mode / Typewriter Mode
- Recent Files
- Last Opened Directory
- Window Size

### Testing & Quality Checks

We have added three types of basic validations to this version.

#### 1. Compilation Check

```
python -m compileall -q .
```

#### 2. Unit Testing

```
python -m unittest discover -s tests -v
```

#### 3. GUI Smoke Testing

We have verified these critical paths in a headless environment:

- Application startup
- Open document
- Mode switching
- Theme switching
- Language switching
- Project search
- Markdown table formatting
- HTML / PDF export

## Current Boundaries

We are well aware of the positioning of this version:

It is a **runnable, maintainable, and evolvable project skeleton**, but it does not yet cover all advanced features.

Directions that are not fully covered yet include:

- Full WYSIWYG editing experience
- Math formula rendering
- Image pasting and attachment management
- Mermaid / Chart ecosystem
- More complex shortcut system
- Multi-window support
- Plugin mechanism
- Finer-grained theme system
- Auto-update and installation packages

------

## Future Expansion Directions

If we continue to develop this forward, we will prioritize:

1. Rich text / WYSIWYG editing model
2. Math formula support
3. Image and attachment management
4. Mermaid / Vega chart support
5. Editor capability enhancements
6. Multi-window
7. Plugin system
8. Theme system upgrades
9. More complete internationalization
