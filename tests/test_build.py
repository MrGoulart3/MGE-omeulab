"""Verifica segurança da renderização e estrutura do site gerado."""

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build", ROOT / "build.py")
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class BuildTest(unittest.TestCase):
    def test_untrusted_metadata_cannot_insert_html(self) -> None:
        rendered = BUILD.render_publications([{
            "t": '<script>alert(1)</script>', "a": '<img src=x onerror=alert(1)>',
            "doi": '10.1234/a" onclick="alert(1)', "k": "other"
        }])
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("<img ", rendered)
        self.assertNotIn('onclick="', rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_inline_json_cannot_close_script(self) -> None:
        value = [{"t": "</script><script>bad()</script>"}]
        encoded = BUILD.json_for_html(value)
        self.assertNotIn("</script>", encoded)
        self.assertEqual(value, json.loads(encoded))

    def test_generated_page_and_inline_javascript(self) -> None:
        text = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotRegex(text, r"\{\{[A-Z_]+\}\}")
        self.assertLess(text.index("<title>"), text.index("</head>"))
        self.assertIn('aria-controls="nav-links"', text)
        self.assertIn('id="conteudo" tabindex="-1"', text)
        items = json.loads((ROOT / "src/publicacoes.json").read_text())
        self.assertEqual(len(items), text.count('<li class="pub"'))
        for attributes, content in re.findall(r"<script([^>]*)>(.*?)</script>", text, re.S):
            if 'type="application/' in attributes:
                json.loads(content)
            else:
                result = subprocess.run(["node", "--check"], input=content, text=True, capture_output=True)
                self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("fonts.googleapis.com", text)

    def test_deploy_artifact_contains_only_public_assets(self) -> None:
        expected = {
            "index.html", "404.html", "CNAME", ".nojekyll", "sitemap.xml", "robots.txt",
        } | {"assets/" + f.name for f in (ROOT / "assets").iterdir() if f.suffix in (".jpg", ".png", ".svg")}
        actual = {str(path.relative_to(ROOT / "_site")) for path in (ROOT / "_site").rglob("*") if path.is_file()}
        self.assertEqual(expected, actual)
        self.assertEqual("omeulab.com\n", (ROOT / "_site/CNAME").read_text())


if __name__ == "__main__":
    unittest.main()
