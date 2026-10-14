"""Gera o site estático e a prévia a partir das fontes locais, sem rede."""

from __future__ import annotations

import html
import json
from pathlib import Path
import re
import shutil
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
URL = "https://omeulab.com"
KINDS = {
    "art": ("Artigo", "Article"),
    "pre": ("Preprint", "Preprint"),
    "cong": ("Congresso", "Conference"),
    "other": ("Obra", "Work"),
}
DESCRIPTION = (
    "Mário Goulart Envall — química teórica e computacional, cinética e estados "
    "de transição. Pesquisa, publicações, prêmios e divulgação científica."
)


def render_publications(items: list[dict]) -> str:
    """Renderiza referências legíveis mesmo quando JavaScript está desativado."""
    output = []
    for item in items:
        if not isinstance(item, dict) or not item.get("t"):
            raise ValueError("Cada publicação precisa de um título.")
        kind = item.get("k", "other")
        if kind not in KINDS:
            raise ValueError(f"Tipo de publicação desconhecido: {kind}")
        pt, en = KINDS[kind]
        title = html.escape(str(item["t"]))
        authors = html.escape(str(item.get("a", "")))
        venue = html.escape(str(item.get("v", "")))
        year = html.escape(str(item.get("y") or "s.d."))
        doi = str(item.get("doi", ""))
        reference = ""
        if doi:
            href = html.escape("https://doi.org/" + quote(doi, safe="/():.-_"))
            reference = f' · <a href="{href}">doi:{html.escape(doi)}</a>'
        award = ""
        if item.get("aw"):
            award = f'<span class="award">★ {html.escape(str(item["aw"]))}</span>'
        output.append(
            f'<li class="pub" data-k="{kind}"><div><div class="yr">{year}</div>'
            f'<span class="kind"><span lang="pt">{pt}</span>'
            f'<span lang="en">{en}</span></span></div><div>'
            f'<div class="t">{title}</div><div class="a">{authors}</div>'
            f'<div class="v">{venue}{reference}</div>{award}</div></li>'
        )
    return "\n".join(output)


def json_for_html(value: object) -> str:
    """Impede que conteúdo JSON termine o elemento script."""
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def metadata() -> str:
    """Retorna metadados usando somente informações já presentes no site."""
    person = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": "Mário Goulart Envall",
        "url": URL + "/",
        "sameAs": [
            "https://www.instagram.com/mrgoulart3/",
            "https://github.com/MrGoulart3",
            "http://lattes.cnpq.br/7173567211044314",
        ],
    }
    description = html.escape(DESCRIPTION, quote=True)
    return f'''<link rel="canonical" href="{URL}/">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<meta name="theme-color" content="#f6f4ef">
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:locale:alternate" content="en_US">
<meta property="og:site_name" content="O Meu Laboratório">
<meta property="og:title" content="O Meu Laboratório">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{URL}/">
<meta property="og:image" content="{URL}/assets/hdl_video.jpg">
<meta property="og:image:width" content="320">
<meta property="og:image:height" content="180">
<meta property="og:image:alt" content="Adsorção de gases em hidróxidos duplos lamelares">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="O Meu Laboratório">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{URL}/assets/hdl_video.jpg">
<meta name="twitter:image:alt" content="Adsorção de gases em hidróxidos duplos lamelares">
<script type="application/ld+json">{json_for_html(person)}</script>'''


def main() -> None:
    """Atualiza a página, a 404 e um diretório de publicação sem fontes internas."""
    source = (ROOT / "src/body.html").read_text(encoding="utf-8")
    items = json.loads((ROOT / "src/publicacoes.json").read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise ValueError("src/publicacoes.json deve conter uma lista.")
    source = source.replace("{{PUBLICACOES_HTML}}", render_publications(items))
    source = source.replace("{{PUBLICACOES_JSON}}", json_for_html(items))
    source = source.replace("{{DIPIRONA_JSON}}", (ROOT / "src/dipirona.json").read_text(encoding="utf-8").strip())
    if re.search(r"\{\{[A-Z_]+\}\}", source):
        raise ValueError("Existe um marcador de build sem substituição.")
    head, body = source.split("<!-- /head -->", 1)
    document = (
        '<!doctype html>\n<html lang="pt-BR" data-lang="pt">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
        + head + metadata() + "\n</head>\n<body>\n" + body + "\n</body>\n</html>\n"
    )
    # Site publicado: sem a faixa de prévia nem as marcações "confirmar" (ficam só em _preview.html)
    document = re.sub(r'<div class="preview" id="previewbar">.*?</div>\s*', "", document, count=1, flags=re.S)
    document = re.sub(r'\s*<span class="pend">[^<]*</span>', "", document)
    (ROOT / "index.html").write_text(document, encoding="utf-8")
    # Prévia no Claude: imagens embutidas (a página não carrega arquivos relativos)
    import base64
    def inline(m):
        f = ROOT / m.group(1)
        mime = "image/svg+xml" if f.suffix == ".svg" else "image/png" if f.suffix == ".png" else "image/jpeg"
        return 'src="data:%s;base64,%s"' % (mime, base64.b64encode(f.read_bytes()).decode())
    (ROOT / "_preview.html").write_text(re.sub(r'src="(assets/[^"]+)"', inline, head + body), encoding="utf-8")
    style = re.search(r"<style>.*?</style>", head, re.S).group()
    error_page = f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Página não encontrada · O Meu Laboratório</title>
<meta name="robots" content="noindex">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
{style}</head><body><header class="hero"><div class="wrap"><div>
<a class="brand" href="/">O Meu Lab<b>‡</b></a>
<h1>404 · Página não encontrada</h1>
<p class="lead">O endereço pode ter mudado. Volte à página inicial para continuar.</p>
<p lang="en">Page not found. Return to the homepage to continue.</p>
<a class="btn primary" href="/">Voltar ao início</a>
</div></div></header></body></html>
'''
    (ROOT / "404.html").write_text(error_page, encoding="utf-8")
    target = ROOT / "_site"
    target.mkdir(exist_ok=True)
    for name in ("index.html", "404.html", "CNAME", ".nojekyll", "sitemap.xml", "robots.txt"):
        shutil.copyfile(ROOT / name, target / name)
    (target / "assets").mkdir(exist_ok=True)
    for f in (ROOT / "assets").iterdir():
        if f.suffix in (".jpg", ".png", ".svg"):
            shutil.copyfile(f, target / "assets" / f.name)
    print(f"Build concluído: {len(items)} publicações; saída em index.html e _site/.")


if __name__ == "__main__":
    main()
