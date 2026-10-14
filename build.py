"""Gera o site estático e a prévia a partir das fontes locais, sem rede."""

from __future__ import annotations

import html
import json
from pathlib import Path
import re
import shutil
import unicodedata
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


def metadata(
    path: str = "/",
    title: str = "O Meu Laboratório",
    description: str = DESCRIPTION,
) -> str:
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
    description = html.escape(description, quote=True)
    title = html.escape(title, quote=True)
    return f'''<link rel="canonical" href="{URL}{path}">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<meta name="theme-color" content="#f6f4ef">
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:locale:alternate" content="en_US">
<meta property="og:site_name" content="O Meu Laboratório">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{URL}{path}">
<meta property="og:image" content="{URL}/assets/hdl_video.jpg">
<meta property="og:image:width" content="320">
<meta property="og:image:height" content="180">
<meta property="og:image:alt" content="Adsorção de gases em hidróxidos duplos lamelares">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{URL}/assets/hdl_video.jpg">
<meta name="twitter:image:alt" content="Adsorção de gases em hidróxidos duplos lamelares">
<script type="application/ld+json">{json_for_html(person)}</script>'''


def alphabetical_key(value: str) -> str:
    """Normaliza nomes para ordenação e agrupamento sem acentos."""
    return "".join(
        char for char in unicodedata.normalize("NFD", value)
        if not unicodedata.combining(char)
    ).casefold()


def glossary_letter(name: str) -> str:
    """Retorna a letra inicial ou o grupo numérico de um nome."""
    initial = alphabetical_key(name)[0].upper()
    return "0-9" if initial.isdigit() else initial


def validate_glossary(terms: object) -> None:
    """Rejeita dados incompletos e âncoras repetidas antes da geração."""
    if not isinstance(terms, list) or len(terms) < 70:
        raise ValueError("O glossário precisa de uma lista com ao menos 70 termos.")
    anchors = set()
    reserved = {
        "inicio", "conteudo", "glossario", "referencias", "nav-links",
        "theme-toggle", "site-script", "glossary-script",
    }
    for term in terms:
        if not isinstance(term, dict):
            raise ValueError("Cada termo precisa ser um objeto.")
        anchor = term.get("id", "")
        if not isinstance(anchor, str) or not re.fullmatch(
            r"[a-z0-9]+(?:-[a-z0-9]+)*", anchor
        ):
            raise ValueError("Âncora inválida no glossário.")
        if (
            anchor in anchors or anchor in reserved
            or anchor.startswith(("letter-", "glossary-"))
        ):
            raise ValueError(f"Âncora repetida ou reservada: {anchor}")
        anchors.add(anchor)
        for language in ("pt", "en"):
            translated = term.get(language)
            if not isinstance(translated, dict) or any(
                not isinstance(translated.get(field), str) or not translated[field].strip()
                for field in ("name", "definition")
            ):
                raise ValueError(
                    f"O termo {anchor} precisa de nome e definição em {language}."
                )
            if not re.fullmatch(r"[A-Z]|0-9", glossary_letter(translated["name"])):
                raise ValueError(f"Inicial inválida no termo {anchor}.")


def render_glossary(terms: list[dict]) -> str:
    """Gera verbetes bilíngues com âncoras únicas e grupos alfabéticos."""
    validate_glossary(terms)
    letters = sorted({
        glossary_letter(term[language]["name"])
        for term in terms for language in ("pt", "en")
    })
    ordered = sorted(terms, key=lambda term: alphabetical_key(term["pt"]["name"]))
    groups = {letter: [] for letter in letters}
    for term in ordered:
        anchor = term["id"]
        names = " ".join(
            f'data-{language}="{html.escape(term[language]["name"], quote=True)}"'
            for language in ("pt", "en")
        )
        paragraphs = []
        for language in ("pt", "en"):
            name = html.escape(term[language]["name"])
            definition = html.escape(term[language]["definition"])
            label = "Link deste termo" if language == "pt" else "Link to this term"
            paragraphs.append(
                f'<h3 lang="{language}">{name} <a href="#{anchor}" '
                f'aria-label="{label}">#</a></h3>'
                f'<p lang="{language}">{definition}</p>'
            )
        groups[glossary_letter(term["pt"]["name"])].append(
            f'<article class="card glossary-term" id="{anchor}" {names}>'
            + "".join(paragraphs) + "</article>"
        )
    alphabet_links = []
    for letter in letters:
        hidden = " hidden" if not groups[letter] else ""
        alphabet_links.append(
            f'<a href="#letter-{letter}" data-letter-link{hidden}>{letter}</a>'
        )
    alphabet = "".join(alphabet_links)
    sections = []
    for letter, entries in groups.items():
        hidden = " hidden" if not entries else ""
        sections.append(
            f'<section class="glossary-group" id="letter-{letter}" '
            f'data-glossary-letter="{letter}" aria-labelledby="heading-{letter}"{hidden}>'
            f'<h2 id="heading-{letter}">{letter}</h2>'
            '<div class="glossary-entries">' + "\n".join(entries) + "</div></section>"
        )
    return f'''<section class="block" id="glossario"><div class="wrap">
<label class="glossary-search" for="glossary-search">
<span lang="pt">Buscar no glossário</span><span lang="en">Search the glossary</span>
<input id="glossary-search" type="search" autocomplete="off" aria-controls="glossary-groups" aria-describedby="glossary-status"></label>
<p id="glossary-status" role="status" aria-live="polite">{len(terms)} <span lang="pt">termos</span><span lang="en">terms</span></p>
<noscript><p lang="pt">Sem JavaScript, use o índice ou a busca do navegador.</p><p lang="en">Without JavaScript, use the index or your browser's find command.</p></noscript>
<nav class="alphabet" aria-label="A–Z">{alphabet}</nav>
<p id="glossary-empty" hidden><span lang="pt">Nenhum termo encontrado. Tente outra palavra.</span><span lang="en">No terms found. Try another word.</span></p>
<div id="glossary-groups">{"".join(sections)}</div>
</div></section>'''


def render_glossary_page(head: str, body: str, content: str, script: str) -> str:
    """Reutiliza estilo, navegação, rodapé e controles da página principal."""
    style = re.search(r"<style>.*?</style>", head, re.S).group()
    navigation = re.search(r'<nav class="nav".*?</nav>', body, re.S).group()
    navigation = re.sub(r'href="#([^"]+)"', r'href="index.html#\1"', navigation)
    navigation = navigation.replace(
        'href="glossario.html"', 'href="glossario.html" aria-current="page"'
    )
    footer = re.search(r"<footer>.*?</footer>", body, re.S).group()
    template = (ROOT / "src/glossario.html").read_text(encoding="utf-8")
    template = template.replace("{{GLOSSARIO_HTML}}", content)
    description = "Glossário bilíngue de química, métodos computacionais e pesquisa científica."
    return (
        '<!doctype html>\n<html lang="pt-BR" data-lang="pt"><head>\n'
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
        '<title>Glossário · O Meu Laboratório</title>\n'
        f'<meta name="description" content="{description}">\n'
        + style + metadata("/glossario.html", "Glossário · O Meu Laboratório", description)
        + '</head><body><a class="skip-link" href="#conteudo">'
        '<span lang="pt">Pular para o conteúdo</span><span lang="en">Skip to content</span></a>'
        + navigation + template + footer
        + f'<script id="site-script">{script}</script>\n'
        + '<script id="glossary-script">'
        + (ROOT / "src/glossario.js").read_text(encoding="utf-8")
        + '</script></body></html>\n'
    )


def main() -> None:
    """Atualiza a página, a 404 e um diretório de publicação sem fontes internas."""
    source = (ROOT / "src/body.html").read_text(encoding="utf-8")
    shared_script = (ROOT / "src/site.js").read_text(encoding="utf-8")
    source = source.replace("{{SITE_SCRIPT}}", shared_script)
    terms = json.loads((ROOT / "src/glossario.json").read_text(encoding="utf-8"))
    glossary = render_glossary(terms)
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
    (ROOT / "glossario.html").write_text(
        render_glossary_page(head, body, glossary, shared_script), encoding="utf-8"
    )
    # Prévia no Claude: imagens embutidas (a página não carrega arquivos relativos)
    import base64
    def inline(m):
        f = ROOT / m.group(1)
        mime = "image/svg+xml" if f.suffix == ".svg" else "image/png" if f.suffix == ".png" else "image/jpeg"
        return 'src="data:%s;base64,%s"' % (mime, base64.b64encode(f.read_bytes()).decode())
    preview_body = body.replace("</main>", glossary + "\n</main>", 1)
    preview_body = preview_body.replace("glossario.html#", "#").replace(
        'href="glossario.html"', 'href="#glossario"'
    )
    preview_body += (
        '<script id="glossary-script">'
        + (ROOT / "src/glossario.js").read_text(encoding="utf-8") + '</script>'
    )
    preview_document = (
        '<!doctype html><html lang="pt-BR" data-lang="pt"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        + head + '</head><body>' + preview_body + '</body></html>'
    )
    (ROOT / "_preview.html").write_text(
        re.sub(r'src="(assets/[^"]+)"', inline, preview_document), encoding="utf-8"
    )
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
    for name in (
        "index.html", "glossario.html", "404.html", "CNAME", ".nojekyll",
        "sitemap.xml", "robots.txt",
    ):
        shutil.copyfile(ROOT / name, target / name)
    (target / "assets").mkdir(exist_ok=True)
    for f in (ROOT / "assets").iterdir():
        if f.suffix in (".jpg", ".png", ".svg"):
            shutil.copyfile(f, target / "assets" / f.name)
    print(
        f"Build concluído: {len(items)} publicações e {len(terms)} termos; "
        "saída em index.html, glossario.html e _site/."
    )


if __name__ == "__main__":
    main()
