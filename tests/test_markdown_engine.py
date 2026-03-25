from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader

from labnote.core.exporters import ExportService
from labnote.core.markdown_engine import MarkdownEngine


SAMPLE = """# LabNote 文档\n\n我在这里测试 **加粗**、代码块和表格。\n\n- [x] 预览\n- [x] 导出\n\n```python\nprint('labnote')\n```\n\n| 字段 | 值 |\n| --- | ---: |\n| 温度 | 42 |\n| 备注 | 中文 PDF 需要正常显示 |\n"""


class MarkdownEngineTests(unittest.TestCase):
    def test_render_builds_toc_and_html(self) -> None:
        engine = MarkdownEngine()
        rendered = engine.render(SAMPLE, theme_name="Pearl Light", title="LabNote")
        self.assertIn("<html", rendered.html)
        self.assertIn("<table", rendered.html)
        self.assertEqual(1, len(rendered.toc))
        self.assertEqual("LabNote 文档", rendered.toc[0].text)
        self.assertEqual(1, rendered.toc[0].line_number)

    def test_export_html_and_pdf_with_chinese(self) -> None:
        engine = MarkdownEngine()
        exporter = ExportService(engine)
        with tempfile.TemporaryDirectory() as tmp:
            html_path = exporter.export_html(SAMPLE, Path(tmp) / "demo.html", "Pearl Light", "LabNote")
            pdf_path = exporter.export_pdf(SAMPLE, Path(tmp) / "demo.pdf", "LabNote")
            self.assertTrue(html_path.exists())
            self.assertTrue(pdf_path.exists())
            self.assertGreater(html_path.stat().st_size, 100)
            self.assertGreater(pdf_path.stat().st_size, 100)
            self.assertIn("charset=\"utf-8\"", html_path.read_text(encoding="utf-8"))
            extracted = "\n".join(page.extract_text() or "" for page in PdfReader(str(pdf_path)).pages)
            self.assertIn("LabNote 文档", extracted)
            self.assertIn("中文 PDF", extracted)


if __name__ == "__main__":
    unittest.main()
