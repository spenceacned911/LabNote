from __future__ import annotations

import unittest

from labnote.core.tables import MarkdownTableParser


TABLE_TEXT = """# 表格\n\n| 项目 | 数值 | 备注 |\n| --- | ---: | :---: |\n| 温度 | 42 | 正常 |\n| 压力 | 12 | 稳定 |\n"""


class TableTests(unittest.TestCase):
    def test_find_table_at_cursor(self) -> None:
        parser = MarkdownTableParser()
        table = parser.find_at_cursor(TABLE_TEXT, line_number=4)
        self.assertIsNotNone(table)
        assert table is not None
        self.assertEqual(["项目", "数值", "备注"], table.headers)
        self.assertEqual(["left", "right", "center"], table.aligns)
        self.assertEqual(2, len(table.rows))

    def test_to_markdown_keeps_columns_aligned(self) -> None:
        parser = MarkdownTableParser()
        table = parser.find_at_cursor(TABLE_TEXT, line_number=4)
        assert table is not None
        table.rows[0][2] = "中文 mixed"
        markdown = table.to_markdown()
        lines = markdown.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertTrue(lines[0].startswith("| "))
        self.assertIn("中文 mixed", lines[2])
        self.assertIn(":", lines[1])


if __name__ == "__main__":
    unittest.main()
