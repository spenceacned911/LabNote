from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import ListFlowable, ListItem, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle

from labnote.core.markdown_engine import MarkdownEngine


@dataclass(slots=True)
class PdfFontBundle:
    regular: str
    bold: str


_PDF_FONT_BUNDLE: PdfFontBundle | None = None


class ExportService:
    def __init__(self, engine: MarkdownEngine) -> None:
        self.engine = engine

    def export_html(self, text: str, output_path: str | Path, theme_name: str, title: str) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        rendered = self.engine.render(text=text, theme_name=theme_name, title=title)
        output.write_text(rendered.html, encoding="utf-8")
        return output

    def export_pdf(self, text: str, output_path: str | Path, title: str) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        ast = self.engine.parse_ast(text)
        font_bundle = resolve_pdf_fonts()
        styles = self._build_styles(font_bundle)
        story: list[Any] = []
        for node in ast:
            story.extend(self._node_to_flowables(node, styles, font_bundle))
        if not story:
            story.append(Paragraph("(empty document)", styles["LNBody"]))

        doc = SimpleDocTemplate(
            str(output),
            pagesize=A4,
            leftMargin=16 * mm,
            rightMargin=16 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=title,
            author="LabNote",
        )
        doc.build(story)
        return output

    def _build_styles(self, font_bundle: PdfFontBundle) -> StyleSheet1:
        styles = getSampleStyleSheet()
        styles.add(
            ParagraphStyle(
                name="LNBody",
                parent=styles["BodyText"],
                fontName=font_bundle.regular,
                fontSize=11.2,
                leading=18,
                spaceAfter=8,
                wordWrap="CJK",
                textColor=colors.HexColor("#162033"),
            )
        )
        styles.add(
            ParagraphStyle(
                name="LNQuote",
                parent=styles["LNBody"],
                leftIndent=12,
                borderPadding=6,
                borderLeftColor=colors.HexColor("#2962ff"),
                borderLeftWidth=2,
                textColor=colors.HexColor("#51627a"),
                backColor=colors.HexColor("#f5f8ff"),
            )
        )
        styles.add(
            ParagraphStyle(
                name="LNCode",
                parent=styles["LNBody"],
                fontName=font_bundle.regular,
                fontSize=10.2,
                leading=14,
                leftIndent=8,
                rightIndent=8,
                backColor=colors.HexColor("#f4f7fb"),
                borderPadding=6,
                borderColor=colors.HexColor("#d3dbe7"),
                borderWidth=0.5,
                borderRadius=6,
                wordWrap="CJK",
                spaceBefore=4,
                spaceAfter=10,
            )
        )
        for level, size in [(1, 22), (2, 18), (3, 15), (4, 13), (5, 12), (6, 11.4)]:
            styles.add(
                ParagraphStyle(
                    name=f"LNH{level}",
                    parent=styles["Heading1"],
                    fontName=font_bundle.bold,
                    fontSize=size,
                    leading=size + 4,
                    textColor=colors.HexColor("#101827"),
                    wordWrap="CJK",
                    spaceBefore=14,
                    spaceAfter=8,
                    alignment=TA_LEFT,
                )
            )
        return styles

    def _node_to_flowables(self, node: dict[str, Any], styles: StyleSheet1, font_bundle: PdfFontBundle) -> list[Any]:
        node_type = node.get("type")
        if node_type == "heading":
            level = int(node.get("attrs", {}).get("level", 1))
            text = self._inline_to_markup(node.get("children", []), font_bundle) or "Untitled"
            return [Paragraph(text, styles[f"LNH{min(level, 6)}"])]
        if node_type == "paragraph":
            return [Paragraph(self._inline_to_markup(node.get("children", []), font_bundle) or "&nbsp;", styles["LNBody"])]
        if node_type == "block_code":
            language = (node.get("attrs", {}).get("info") or "").strip()
            prefix = f"[{language}]\n" if language else ""
            return [Preformatted(prefix + node.get("raw", ""), styles["LNCode"])]
        if node_type == "list":
            return [self._build_list(node, styles, font_bundle), Spacer(1, 4)]
        if node_type == "table":
            return [self._build_table(node, styles, font_bundle), Spacer(1, 8)]
        if node_type == "block_quote":
            flowables: list[Any] = []
            for child in node.get("children", []):
                if child.get("type") == "paragraph":
                    flowables.append(Paragraph(self._inline_to_markup(child.get("children", []), font_bundle) or "&nbsp;", styles["LNQuote"]))
                else:
                    flowables.extend(self._node_to_flowables(child, styles, font_bundle))
            if not flowables:
                flowables.append(Paragraph("&nbsp;", styles["LNQuote"]))
            return flowables
        if node_type == "thematic_break":
            return [Spacer(1, 10)]
        if node_type == "blank_line":
            return []
        if node_type == "footnotes":
            flowables: list[Any] = [Paragraph("Footnotes", styles["LNH3"])]
            for idx, item in enumerate(node.get("children", []), start=1):
                parts: list[str] = []
                for child in item.get("children", []):
                    if child.get("type") == "paragraph":
                        parts.append(self._inline_to_markup(child.get("children", []), font_bundle))
                flowables.append(Paragraph(f"<b>[{idx}]</b> {' '.join(parts)}", styles["LNBody"]))
            return flowables
        return []

    def _build_list(self, node: dict[str, Any], styles: StyleSheet1, font_bundle: PdfFontBundle) -> ListFlowable:
        ordered = bool(node.get("attrs", {}).get("ordered", False))
        list_items: list[ListItem] = []
        for idx, child in enumerate(node.get("children", []), start=1):
            item_paragraphs = self._list_item_content(child, styles, font_bundle)
            if not item_paragraphs:
                item_paragraphs = [Paragraph("&nbsp;", styles["LNBody"])]
            list_items.append(ListItem(item_paragraphs, value=idx if ordered else None))
        return ListFlowable(list_items, bulletType="1" if ordered else "bullet", start="1", leftIndent=18)

    def _list_item_content(self, node: dict[str, Any], styles: StyleSheet1, font_bundle: PdfFontBundle) -> list[Any]:
        node_type = node.get("type")
        if node_type == "task_list_item":
            checked = bool(node.get("attrs", {}).get("checked", False))
            prefix = "[x] " if checked else "[ ] "
            body: list[Any] = []
            for child in node.get("children", []):
                if child.get("type") == "block_text":
                    body.append(Paragraph(prefix + (self._inline_to_markup(child.get("children", []), font_bundle) or "&nbsp;"), styles["LNBody"]))
                else:
                    body.extend(self._node_to_flowables(child, styles, font_bundle))
            return body
        body: list[Any] = []
        for child in node.get("children", []):
            if child.get("type") == "block_text":
                body.append(Paragraph(self._inline_to_markup(child.get("children", []), font_bundle) or "&nbsp;", styles["LNBody"]))
            else:
                body.extend(self._node_to_flowables(child, styles, font_bundle))
        return body

    def _build_table(self, node: dict[str, Any], styles: StyleSheet1, font_bundle: PdfFontBundle) -> Table:
        rows: list[list[Any]] = []
        for child in node.get("children", []):
            if child.get("type") == "table_head":
                rows.append([Paragraph(f"<b>{self._inline_to_markup(cell.get('children', []), font_bundle)}</b>", styles["LNBody"]) for cell in child.get("children", [])])
            elif child.get("type") == "table_body":
                for row in child.get("children", []):
                    rows.append([Paragraph(self._inline_to_markup(cell.get("children", []), font_bundle) or "&nbsp;", styles["LNBody"]) for cell in row.get("children", [])])
        if not rows:
            rows = [[Paragraph("(empty)", styles["LNBody"])] ]
        usable_width = A4[0] - (16 * mm) - (16 * mm)
        col_count = max(1, len(rows[0]))
        col_widths = [usable_width / col_count] * col_count
        table = Table(rows, colWidths=col_widths, hAlign="LEFT", repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font_bundle.regular),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3fb")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d4dce8")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return table

    def _inline_to_markup(self, nodes: list[dict[str, Any]], font_bundle: PdfFontBundle) -> str:
        parts: list[str] = []
        for node in nodes:
            node_type = node.get("type")
            if node_type == "text":
                parts.append(escape(node.get("raw", "")))
            elif node_type in {"softbreak", "linebreak"}:
                parts.append("<br/>")
            elif node_type == "strong":
                parts.append(f"<b>{self._inline_to_markup(node.get('children', []), font_bundle)}</b>")
            elif node_type == "emphasis":
                parts.append(f"<i>{self._inline_to_markup(node.get('children', []), font_bundle)}</i>")
            elif node_type == "strikethrough":
                parts.append(self._inline_to_markup(node.get("children", []), font_bundle))
            elif node_type == "codespan":
                code = escape(node.get("raw", ""))
                parts.append(f"<font name='{font_bundle.regular}'>{code}</font>")
            elif node_type == "link":
                url = escape(node.get("attrs", {}).get("url", ""), quote=True)
                label = self._inline_to_markup(node.get("children", []), font_bundle) or url
                parts.append(f"<a href='{url}' color='blue'>{label}</a>")
            elif node_type == "image":
                alt = escape(node.get("attrs", {}).get("alt", "image"))
                url = escape(node.get("attrs", {}).get("url", ""))
                parts.append(f"[Image: {alt}] {url}")
            elif node_type in {"inline_math", "block_math"}:
                parts.append(f"<font name='{font_bundle.regular}' color='#2962ff'>{escape(node.get('raw', ''))}</font>")
            elif node_type == "footnote_ref":
                key = escape(str(node.get("raw", "")))
                parts.append(f"<super>[{key}]</super>")
            elif node_type == "task_list_item_marker":
                parts.append(escape(node.get("raw", "")))
            elif "children" in node:
                parts.append(self._inline_to_markup(node.get("children", []), font_bundle))
        return "".join(parts)


def resolve_pdf_fonts() -> PdfFontBundle:
    global _PDF_FONT_BUNDLE
    if _PDF_FONT_BUNDLE is not None:
        return _PDF_FONT_BUNDLE

    candidates = [
        (Path("/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf"), Path("/usr/share/fonts/truetype/arphic-gkai00mp/gkai00mp.ttf")),
        (Path("/usr/share/fonts/truetype/arphic/uming.ttc"), Path("/usr/share/fonts/truetype/arphic/uming.ttc")),
        (Path("C:/Windows/Fonts/simhei.ttf"), Path("C:/Windows/Fonts/simhei.ttf")),
        (Path("C:/Windows/Fonts/msyh.ttf"), Path("C:/Windows/Fonts/msyhbd.ttf")),
        (Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"), Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")),
        (Path("/Library/Fonts/Arial Unicode.ttf"), Path("/Library/Fonts/Arial Unicode.ttf")),
    ]
    for regular_path, bold_path in candidates:
        bundle = _try_register_font_pair(regular_path, bold_path)
        if bundle:
            _PDF_FONT_BUNDLE = bundle
            return bundle

    try:
        if "STSong-Light" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        _PDF_FONT_BUNDLE = PdfFontBundle(regular="STSong-Light", bold="STSong-Light")
        return _PDF_FONT_BUNDLE
    except Exception:
        _PDF_FONT_BUNDLE = PdfFontBundle(regular="Helvetica", bold="Helvetica-Bold")
        return _PDF_FONT_BUNDLE


def _try_register_font_pair(regular_path: Path, bold_path: Path) -> PdfFontBundle | None:
    if not regular_path.exists():
        return None
    try:
        if regular_path.suffix.lower() == ".ttc":
            pdfmetrics.registerFont(TTFont("LabNoteSans", str(regular_path), subfontIndex=0))
        else:
            pdfmetrics.registerFont(TTFont("LabNoteSans", str(regular_path)))
        if bold_path.exists():
            if bold_path.suffix.lower() == ".ttc":
                pdfmetrics.registerFont(TTFont("LabNoteSansBold", str(bold_path), subfontIndex=0))
            else:
                pdfmetrics.registerFont(TTFont("LabNoteSansBold", str(bold_path)))
        else:
            pdfmetrics.registerFont(TTFont("LabNoteSansBold", str(regular_path)))
    except Exception:
        return None
    return PdfFontBundle(regular="LabNoteSans", bold="LabNoteSansBold")
