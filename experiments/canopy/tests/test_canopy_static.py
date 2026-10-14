"""Offline static assurance checks for the C1 fictional Canopy demo."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

SITE = Path(__file__).resolve().parents[1] / "site"
INDEX = (SITE / "index.html").read_text(encoding="utf-8")
SCRIPT = (SITE / "app.js").read_text(encoding="utf-8")
CSS = (SITE / "style.css").read_text(encoding="utf-8")
README = (SITE.parent / "README.md").read_text(encoding="utf-8")


class ResourceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.external = []
        self.ids = set()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag in ("script", "link", "img", "iframe"):
            url = attrs.get("src") or attrs.get("href")
            if url:
                self.links.append(url)
                if "://" in url or url.startswith("//"):
                    self.external.append(url)


class CanopyContractTests(unittest.TestCase):
    def test_no_external_dependencies(self):
        parsed = ResourceParser()
        parsed.feed(INDEX)
        self.assertFalse(parsed.external)
        self.assertEqual(set(parsed.links), {"./app.js", "./style.css"})
        for link in parsed.links:
            self.assertTrue((SITE / link.removeprefix("./")).is_file())

    def test_interaction_surfaces_exist(self):
        parsed = ResourceParser()
        parsed.feed(INDEX)
        self.assertTrue({"nodeSelect", "nodeName", "storyBtn", "postcardBtn",
                         "noteForm", "noteInput", "noteList", "neighborList"} <= parsed.ids)

    def test_offline_no_unsafe_browser_apis(self):
        for forbidden in ("fetch(", "WebSocket", "localStorage", "sessionStorage",
                          "geolocation", "mediaDevices", "innerHTML", "eval(",
                          "XMLHttpRequest"):
            self.assertNotIn(forbidden, SCRIPT)
        self.assertIn("textContent = value", SCRIPT)
        self.assertIn('maxlength="120"', INDEX.lower())

    def test_demo_boundaries(self):
        for value in ("PHIPIE-DEMO-001", "PHIPIE-DEMO-002",
                      "PHIPIE-DEMO-003", "PHIPIE-DEMO-004"):
            self.assertIn(value, SCRIPT)
        self.assertIn("No live Wi-Fi", INDEX)
        self.assertIn("PHIPIE-03", README)
        self.assertIn("prefers-reduced-motion", CSS)


if __name__ == "__main__":
    unittest.main()
