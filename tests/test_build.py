"""Verifica segurança da renderização e estrutura do site gerado."""

import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET

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
        for name in ("index.html", "glossario.html", "_preview.html"):
            page = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotRegex(page, r"\{\{[A-Z_]+\}\}")
            self.assertNotRegex(page.casefold(), r"atômicos|atomicos|anchor\.fm")
            for attributes, content in re.findall(r"<script([^>]*)>(.*?)</script>", page, re.S):
                if " src=" in attributes:
                    continue
                if 'type="application/' in attributes:
                    json.loads(content)
                else:
                    result = subprocess.run(["node", "--check"], input=content, text=True, capture_output=True)
                    self.assertEqual(0, result.returncode, f"{name}: {result.stderr}")
        self.assertNotIn("fonts.googleapis.com", text)
        for script in ("site.js", "pubs.js", "mol.js", "glossario.js"):
            result = subprocess.run(["node", "--check", str(ROOT / "assets" / script)], capture_output=True, text=True)
            self.assertEqual(0, result.returncode, f"{script}: {result.stderr}")

    def test_glossary_data_and_unique_anchors(self) -> None:
        terms = json.loads((ROOT / "src/glossario.json").read_text(encoding="utf-8"))
        BUILD.validate_glossary(terms)
        self.assertGreaterEqual(len(terms), 70)
        required = {
            "hdl", "nox-sox", "poa", "aduto", "ozonio", "tom", "dft",
            "funcional", "m08-hx", "m06-2x", "conjunto-de-base", "aug-cc-pvdz",
            "solvatacao-implicita", "solvatacao-explicita", "smd", "pcm",
            "estado-de-transicao", "frequencia-imaginaria", "irc", "tst",
            "tunelamento-quantico", "wigner", "eckart", "bell", "skodje-truhlar",
            "transitivity", "xtb", "crest", "gaussian", "orca", "sella",
            "dipirona", "4-maa", "hplc", "ftir", "pfas", "pfos",
            "tia-michael", "doi", "preprint", "orcid", "lattes",
        }
        self.assertTrue(required <= {term["id"] for term in terms})
        for term in terms:
            for language in ("pt", "en"):
                with self.subTest(term=term["id"], language=language):
                    self.assertTrue(term[language]["name"].strip())
                    definition = term[language]["definition"]
                    sentences = re.split(r"(?<=[.!?])\s+", definition)
                    self.assertGreaterEqual(len(sentences), 2)
                    self.assertLessEqual(len(sentences), 4)
        for name in ("glossario.html", "_preview.html"):
            text = (ROOT / name).read_text(encoding="utf-8")
            ids = re.findall(r'\bid="([^"]+)"', text)
            self.assertEqual(len(ids), len(set(ids)), name)
            self.assertEqual(len(terms), text.count('class="card glossary-term"'))
            for term in terms:
                self.assertIn(f'id="{term["id"]}"', text)
                self.assertIn(f'href="#{term["id"]}"', text)

    def test_glossary_rejects_incomplete_or_conflicting_data(self) -> None:
        terms = json.loads((ROOT / "src/glossario.json").read_text(encoding="utf-8"))
        for change in ("duplicate", "language", "anchor", "reserved"):
            broken = copy.deepcopy(terms)
            if change == "duplicate":
                broken[1]["id"] = broken[0]["id"]
            elif change == "language":
                del broken[0]["en"]
            elif change == "reserved":
                broken[0]["id"] = "conteudo"
            else:
                broken[0]["id"] = 'bad" onclick="alert(1)'
            with self.subTest(change=change), self.assertRaises(ValueError):
                BUILD.render_glossary(broken)
        with self.assertRaises(ValueError):
            BUILD.render_glossary(terms[:6])

    def test_glossary_escapes_names_and_definitions(self) -> None:
        terms = json.loads((ROOT / "src/glossario.json").read_text(encoding="utf-8"))
        terms[0]["pt"]["name"] = 'A <img src=x onerror=alert(1)> "'
        terms[0]["pt"]["definition"] = '<script>alert(1)</script>'
        rendered = BUILD.render_glossary(terms)
        self.assertNotIn("<img ", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("&quot;", rendered)

    def test_glossary_navigation_metadata_and_shared_visual(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        glossary = (ROOT / "glossario.html").read_text(encoding="utf-8")
        self.assertNotIn('<details class="gl">', index)
        self.assertNotIn('class="card glossary-term"', index)
        self.assertGreaterEqual(index.count('href="glossario.html"'), 3)
        for tag in ("nav", "footer"):
            part = re.search(rf"<{tag}\b.*?</{tag}>", index, re.S).group()
            self.assertIn('href="glossario.html"', part)
        ids = set(re.findall(r'\bid="([^"]+)"', glossary))
        for anchor in re.findall(r'href="glossario.html#([^"]+)"', index):
            self.assertIn(anchor, ids)
        self.assertEqual(
            re.search(r'<link rel="stylesheet" href="[^"]+">', index).group(),
            re.search(r'<link rel="stylesheet" href="[^"]+">', glossary).group(),
        )
        self.assertIn('href="https://omeulab.com/glossario.html"', glossary)
        self.assertIn('content="https://omeulab.com/glossario.html"', glossary)
        for markup in ('data-setlang="pt"', 'data-setlang="en"', 'id="theme-toggle"', 'aria-controls="nav-links"'):
            self.assertIn(markup, glossary)
        sitemap = ET.parse(ROOT / "sitemap.xml")
        locations = [node.text for node in sitemap.findall(".//{*}loc")]
        self.assertIn("https://omeulab.com/glossario.html", locations)

    def test_deploy_artifact_contains_only_public_assets(self) -> None:
        suffixes = {".jpg", ".png", ".svg", ".webp", ".css", ".js", ".woff2", ".txt"}
        expected = {
            "index.html", "glossario.html", "404.html", "CNAME", ".nojekyll", "sitemap.xml",
            "robots.txt", "favicon.ico", "manifest.webmanifest",
        } | {
            "assets/" + str(f.relative_to(ROOT / "assets"))
            for f in (ROOT / "assets").rglob("*") if f.is_file() and f.suffix in suffixes
        }
        actual = {str(path.relative_to(ROOT / "_site")) for path in (ROOT / "_site").rglob("*") if path.is_file()}
        self.assertEqual(expected, actual)
        self.assertEqual("omeulab.com\n", (ROOT / "_site/CNAME").read_text())
        for name in ("index.html", "glossario.html", "sitemap.xml"):
            self.assertEqual((ROOT / name).read_bytes(), (ROOT / "_site" / name).read_bytes())

    def test_published_pages_have_no_inline_code_and_reference_existing_files(self) -> None:
        for name in ("index.html", "glossario.html", "404.html"):
            page = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("Content-Security-Policy", page)
            self.assertNotIn("unsafe-inline", page)
            self.assertNotIn("unsafe-eval", page)
            self.assertNotRegex(page, r'\sstyle="')
            self.assertNotIn("<style", page)
            self.assertNotRegex(page, r"\son[a-z]+=")
            for attributes, content in re.findall(r"<script([^>]*)>(.*?)</script>", page, re.S):
                if " src=" not in attributes:
                    self.assertRegex(attributes, r'type="application/(ld\+)?json"')
            for reference in re.findall(r'(?:href|src|srcset)="/(?:assets/)?([^"?\s,]+)', page):
                candidates = [ROOT / reference, ROOT / "assets" / reference]
                self.assertTrue(any(c.is_file() for c in candidates), f"{name}: {reference}")

    def test_fonts_images_icons_and_social_card(self) -> None:
        css = (ROOT / "assets/site.css").read_text(encoding="utf-8")
        for family in ("Fraunces", "IBM Plex Sans", "IBM Plex Mono"):
            self.assertIn(f'@font-face{{font-family:"{family}"', css)
        self.assertNotIn("fonts.googleapis", css)
        for file in re.findall(r"url\(fonts/([^)]+)\)", css):
            self.assertTrue((ROOT / "assets/fonts" / file).is_file(), file)
        self.assertEqual(css.count("font-display:swap"), css.count("@font-face"))
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertEqual(2, index.count('rel="preload"'))
        self.assertIn('<meta name="twitter:card" content="summary_large_image">', index)
        self.assertIn('content="1200"', index)
        from PIL import Image
        for name, size in (("og.png", (1200, 630)), ("apple-touch-icon.png", (180, 180))):
            with Image.open(ROOT / "assets" / name) as image:
                self.assertEqual(size, image.size)
        self.assertTrue((ROOT / "favicon.ico").is_file())
        manifest = json.loads((ROOT / "manifest.webmanifest").read_text())
        for icon in manifest["icons"]:
            self.assertTrue((ROOT / icon["src"].lstrip("/")).is_file())
        self.assertIn('media="(prefers-color-scheme: dark)"', index)
        for image in re.findall(r"<img [^>]*>", index):
            self.assertRegex(image, r'width="\d+"')
            self.assertRegex(image, r'height="\d+"')
            self.assertRegex(image, r'alt="[^"]+"')
        self.assertIn("lattes.cnpq.br", index)
        self.assertNotIn("http://lattes", index)

    def test_structured_data_covers_person_publications_and_glossary(self) -> None:
        def graph(name: str) -> list:
            page = (ROOT / name).read_text(encoding="utf-8")
            block = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S).group(1)
            return json.loads(block)["@graph"]
        home = graph("index.html")
        types = [node["@type"] for node in home]
        self.assertIn("WebSite", types)
        person = next(node for node in home if node["@type"] == "Person")
        for key in ("jobTitle", "affiliation", "sameAs", "knowsAbout"):
            self.assertIn(key, person)
        self.assertTrue(all(link.startswith("https://") for link in person["sameAs"]))
        items = json.loads((ROOT / "src/publicacoes.json").read_text())
        self.assertEqual(len(items), types.count("ScholarlyArticle"))
        terms = json.loads((ROOT / "src/glossario.json").read_text(encoding="utf-8"))
        termset = next(node for node in graph("glossario.html") if node["@type"] == "DefinedTermSet")
        self.assertEqual(len(terms), len(termset["hasDefinedTerm"]))

    def test_sitemap_has_lastmod(self) -> None:
        sitemap = ET.parse(ROOT / "sitemap.xml")
        mods = [node.text for node in sitemap.findall(".//{*}lastmod")]
        self.assertEqual(2, len(mods))
        for mod in mods:
            self.assertRegex(mod, r"^\d{4}-\d{2}-\d{2}$")


if __name__ == "__main__":
    unittest.main()
