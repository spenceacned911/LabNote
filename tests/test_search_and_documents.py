from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from labnote.app.document_manager import DocumentManager
from labnote.core.search import ProjectSearcher


class SearchAndDocumentTests(unittest.TestCase):
    def test_search_in_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "one.md").write_text("hello labnote\npreview panel\n", encoding="utf-8")
            (root / "two.txt").write_text("nothing\nlabnote again\n", encoding="utf-8")
            results = ProjectSearcher().search(root, "labnote")
            self.assertEqual(2, len(results))
            self.assertEqual(root / "one.md", results[0].file_path)

    def test_document_manager_roundtrip(self) -> None:
        manager = DocumentManager()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "demo.md"
            path.write_text("# demo\n", encoding="utf-8")
            document = manager.open_file(path)
            self.assertEqual("# demo\n", document.content)
            document.content = "# changed\n"
            document.mark_dirty()
            manager.save_document(document)
            self.assertEqual("# changed\n", path.read_text(encoding="utf-8"))
            reloaded = manager.reload_from_disk(document)
            self.assertEqual("# changed\n", reloaded.content)


if __name__ == "__main__":
    unittest.main()
