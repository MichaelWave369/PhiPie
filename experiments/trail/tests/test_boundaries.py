import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BoundaryTests(unittest.TestCase):
    def test_runtime_does_not_import_archived_source(self):
        for file in (ROOT / "trailcore").glob("*.py"):
            body = file.read_text()
            self.assertNotIn("reference.", body)
            self.assertNotIn("ai.telemetry_mesh", body)

    def test_no_embedded_credentials_or_database(self):
        banned = {".env", ".pem", ".key", ".p12", ".pfx", ".sqlite", ".sqlite3", ".db"}
        for file in ROOT.rglob("*"):
            if file.is_file():
                self.assertFalse(any(file.name.endswith(suffix) for suffix in banned), str(file))
