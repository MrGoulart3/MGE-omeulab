# O Meu Laboratório

**English** · [Português brasileiro](README.pt-BR.md)

Source of [omeulab.com](https://omeulab.com), the bilingual (PT/EN) personal research hub of Mário Goulart Envall:
research, publications, awards, science outreach, code and contact.

- Static site, no framework: content in `src/body.html`, publications in `src/publicacoes.json`.
- Styles and scripts live in `assets/` (`site.css`, `*.js`, self-hosted fonts); `scripts/make_images.py` regenerates WebP, the social card and icons (needs Pillow).
- `python3 build.py` generates `index.html`, `404.html` and the publish folder `_site/`.
- `scripts/orcid_sync.py <ORCID-iD>` refreshes the publication list from the public ORCID API.
- Deployed with GitHub Pages through the manual workflow `.github/workflows/pages.yml` (tests run first).

Local checks:

```bash
python3 build.py
python3 -m unittest discover -s tests -v
node --test --test-isolation=none tests/site_runtime.test.cjs
```

Content © Mário Goulart Envall. Code under the MIT license.
