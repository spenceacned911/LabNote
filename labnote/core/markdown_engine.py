from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

import mistune
from mistune.plugins.abbr import abbr
from mistune.plugins.def_list import def_list
from mistune.plugins.footnotes import footnotes
from mistune.plugins.formatting import insert, mark, strikethrough, subscript, superscript
from mistune.plugins.math import math
from mistune.plugins.table import table
from mistune.plugins.task_lists import task_lists
from mistune.plugins.url import url
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.lexers.special import TextLexer

from labnote.core.toc import HeadingEntry, TableOfContentsExtractor


PLUGINS = [table, task_lists, def_list, footnotes, url, abbr, math, strikethrough, mark, insert, superscript, subscript]


class HighlightingHTMLRenderer(mistune.HTMLRenderer):
    def __init__(self) -> None:
        super().__init__(escape=False)
        self._formatter = HtmlFormatter(cssclass="codehilite", nowrap=False)

    def block_code(self, code: str, info: str | None = None) -> str:
        language = (info or "").strip().split(maxsplit=1)[0]
        lexer = TextLexer()
        if language:
            try:
                lexer = get_lexer_by_name(language, stripall=False)
            except Exception:
                lexer = TextLexer()
        highlighted = highlight(code, lexer, self._formatter)
        return f'<div class="code-wrapper">{highlighted}</div>'

    def codespan(self, text: str) -> str:
        return f"<code>{escape(text)}</code>"

    def image(self, text: str, url: str, title: str | None = None) -> str:
        title_attr = f' title="{escape(title)}"' if title else ""
        alt = escape(text or "image")
        return f'<figure><img src="{escape(url)}" alt="{alt}"{title_attr}/><figcaption>{alt}</figcaption></figure>'


@dataclass(slots=True)
class RenderedMarkdown:
    html: str
    ast: list[dict[str, Any]]
    toc: list[HeadingEntry]


class MarkdownEngine:
    def __init__(self) -> None:
        self.html_renderer = HighlightingHTMLRenderer()
        self.html_markdown = mistune.create_markdown(renderer=self.html_renderer, plugins=PLUGINS)
        self.ast_markdown = mistune.create_markdown(renderer="ast", plugins=PLUGINS)
        self.toc_extractor = TableOfContentsExtractor()
        self.pygments_css = HtmlFormatter(cssclass="codehilite").get_style_defs(".codehilite")

    def render(self, text: str, theme_name: str = "Graphite Dark", title: str = "Document") -> RenderedMarkdown:
        ast = self.parse_ast(text)
        toc = self.toc_extractor.extract(ast, text)
        body_html = self.html_markdown(text)
        html = self.wrap_html(body_html=body_html, theme_name=theme_name, title=title)
        return RenderedMarkdown(html=html, ast=ast, toc=toc)

    def parse_ast(self, text: str) -> list[dict[str, Any]]:
        return self.ast_markdown(text)

    def extract_toc(self, text: str) -> list[HeadingEntry]:
        ast = self.parse_ast(text)
        return self.toc_extractor.extract(ast, text)

    def wrap_html(self, body_html: str, theme_name: str, title: str) -> str:
        theme = self._html_theme(theme_name)
        css = f"""
        :root {{
          color-scheme: {theme['color_scheme']};
        }}
        * {{ box-sizing: border-box; }}
        html, body {{ margin: 0; padding: 0; }}
        body {{
          background: {theme['background']};
          color: {theme['foreground']};
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', 'Noto Sans CJK SC', sans-serif;
          line-height: 1.72;
          font-size: 16px;
        }}
        main {{
          max-width: 960px;
          margin: 0 auto;
          padding: 40px 42px 72px;
        }}
        a {{ color: {theme['accent']}; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        h1, h2, h3, h4, h5, h6 {{
          color: {theme['heading']};
          margin-top: 1.5em;
          margin-bottom: 0.68em;
          line-height: 1.25;
        }}
        h1 {{ font-size: 2.25em; border-bottom: 1px solid {theme['border']}; padding-bottom: 0.32em; }}
        h2 {{ font-size: 1.8em; border-bottom: 1px solid {theme['border']}; padding-bottom: 0.24em; }}
        h3 {{ font-size: 1.42em; }}
        h4 {{ font-size: 1.18em; }}
        code {{
          background: {theme['inline_code_bg']};
          padding: 0.14em 0.42em;
          border-radius: 7px;
          font-family: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace;
        }}
        pre {{ margin: 0; overflow-x: auto; }}
        .code-wrapper {{
          background: {theme['code_bg']};
          border: 1px solid {theme['border']};
          border-radius: 14px;
          padding: 16px 18px;
          margin: 1.25em 0;
          overflow-x: auto;
        }}
        blockquote {{
          margin: 1.25em 0;
          padding: 0.4em 1.1em;
          border-left: 4px solid {theme['accent']};
          color: {theme['muted']};
          background: {theme['quote_bg']};
          border-radius: 10px;
        }}
        table {{
          width: 100%;
          border-collapse: separate;
          border-spacing: 0;
          margin: 1.25em 0;
          border: 1px solid {theme['border']};
          border-radius: 14px;
          overflow: hidden;
        }}
        th, td {{
          border-bottom: 1px solid {theme['border']};
          border-right: 1px solid {theme['border']};
          padding: 11px 13px;
          text-align: left;
          vertical-align: top;
        }}
        tr:last-child td {{ border-bottom: none; }}
        th:last-child, td:last-child {{ border-right: none; }}
        th {{ background: {theme['table_head_bg']}; color: {theme['heading']}; }}
        hr {{ border: none; border-top: 1px solid {theme['border']}; margin: 2em 0; }}
        img {{ max-width: 100%; border-radius: 12px; }}
        figure {{ margin: 1.2em 0; }}
        figcaption {{ color: {theme['muted']}; font-size: 0.92em; margin-top: 0.5em; }}
        ul.task-list {{ list-style: none; padding-left: 1.2em; }}
        .math, .math-inline {{
          color: {theme['accent']};
          font-family: 'JetBrains Mono', 'Fira Code', monospace;
        }}
        {self.pygments_css}
        """
        return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{escape(title)}</title>
  <style>{css}</style>
</head>
<body>
  <main>
    {body_html}
  </main>
</body>
</html>
"""

    def _html_theme(self, theme_name: str) -> dict[str, str]:
        is_dark = theme_name.lower() in {"graphite dark", "midnight", "nocturne"} or "dark" in theme_name.lower() or "night" in theme_name.lower()
        if is_dark:
            return {
                "color_scheme": "dark",
                "background": "#12161f",
                "foreground": "#e8edf7",
                "heading": "#f8fbff",
                "muted": "#aab5c8",
                "accent": "#7aa2ff",
                "border": "#2a3345",
                "inline_code_bg": "#1b2331",
                "code_bg": "#0f141d",
                "quote_bg": "#192131",
                "table_head_bg": "#1b2432",
            }
        return {
            "color_scheme": "light",
            "background": "#f4f7fb",
            "foreground": "#182133",
            "heading": "#111827",
            "muted": "#5f6f86",
            "accent": "#2962ff",
            "border": "#d7e0ea",
            "inline_code_bg": "#edf3ff",
            "code_bg": "#f8fbff",
            "quote_bg": "#eef4ff",
            "table_head_bg": "#f0f4fb",
        }


def guess_title_from_path(path: str | Path | None) -> str:
    if path is None:
        return "Untitled"
    return Path(path).name
