"""Gera o site estático e a prévia a partir das fontes locais, sem rede."""

from __future__ import annotations

from datetime import date
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
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
SITE_NAME = "O Meu Laboratório"
HOME_TITLE = "Mário Goulart Envall · Química computacional | Computational chemistry"
HOME_DESCRIPTION = (
    "Química teórica e computacional: estados de transição, cinética e degradação de "
    "fármacos. Publicações, prêmios e divulgação científica de Mário Goulart Envall. / "
    "Theoretical and computational chemistry: transition states, kinetics and drug "
    "degradation. Publications, awards and science outreach."
)
OG_ALT = (
    "Mário Goulart Envall · Química computacional, Ciências farmacêuticas, "
    "com a molécula de dipirona em 3D"
)
PERSON_ID = URL + "/#person"
WEBSITE_ID = URL + "/#website"
SOCIAL = [
    "https://www.instagram.com/mrgoulart3/",
    "https://github.com/MrGoulart3",
    "https://lattes.cnpq.br/7173567211044314",
    "https://www.linkedin.com/in/mario-goulart-envall-7b3143200/",
    "https://x.com/mrgoulart3",
]
# CSP via <meta> (GitHub Pages não permite cabeçalhos). O 3Dmol vem do jsDelivr, com SRI.
CSP = (
    "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self'; "
    "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; object-src 'none'; "
    "base-uri 'self'; form-action 'none'"
)
ASSET_SUFFIXES = {".jpg", ".png", ".svg", ".webp", ".css", ".js", ".woff2", ".txt"}
ROOT_FILES = ("favicon.ico", "manifest.webmanifest")
PRELOAD_FONTS = ("fraunces-latin-opsz-normal.woff2", "ibm-plex-sans-latin-400-normal.woff2")


def asset(name: str) -> str:
    """Caminho absoluto do arquivo em assets/ com versão (hash) para invalidar o cache."""
    digest = hashlib.sha256((ROOT / "assets" / name).read_bytes()).hexdigest()[:8]
    return f"/assets/{name}?v={digest}"


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


def person_node() -> dict:
    """Pessoa com dados que já constam do site (nada presumido)."""
    return {
        "@type": "Person",
        "@id": PERSON_ID,
        "name": "Mário Goulart Envall",
        "url": URL + "/",
        "image": URL + "/assets/foto_mario.jpg",
        "jobTitle": "Analista Pleno de Desenvolvimento Analítico",
        "worksFor": {"@type": "Organization", "name": "Brainfarma"},
        "affiliation": {
            "@type": "CollegeOrUniversity",
            "name": "Universidade Estadual de Goiás (UEG)",
        },
        "alumniOf": {
            "@type": "CollegeOrUniversity",
            "name": "Universidade Estadual de Goiás (UEG)",
        },
        "knowsAbout": [
            "Computational chemistry", "Transition state theory", "Chemical kinetics",
            "Drug degradation", "Density functional theory", "Layered double hydroxides",
            "Analytical development", "Science communication",
        ],
        "sameAs": SOCIAL,
    }


def website_node() -> dict:
    return {
        "@type": "WebSite",
        "@id": WEBSITE_ID,
        "url": URL + "/",
        "name": SITE_NAME,
        "inLanguage": ["pt-BR", "en"],
        "publisher": {"@id": PERSON_ID},
    }


def publication_nodes(items: list[dict]) -> list[dict]:
    """ScholarlyArticle para cada publicação de src/publicacoes.json."""
    nodes = []
    for index, item in enumerate(items):
        authors = []
        for name in (n.strip() for n in str(item.get("a", "")).split(", ") if n.strip()):
            if name.startswith("Envall M. G."):
                authors.append({"@type": "Person", "@id": PERSON_ID, "name": "Mário Goulart Envall"})
            else:
                authors.append({"@type": "Person", "name": name})
        node = {
            "@type": "ScholarlyArticle",
            "@id": f"{URL}/#pub-{index + 1}",
            "headline": item["t"],
            "name": item["t"],
            "author": authors,
            "isPartOf": {"@type": "CreativeWork", "name": item.get("v", "")},
        }
        if item.get("y"):
            node["datePublished"] = str(item["y"])
        if item.get("doi"):
            doi_url = "https://doi.org/" + quote(str(item["doi"]), safe="/():.-_")
            node["url"] = doi_url
            node["sameAs"] = doi_url
            node["identifier"] = {
                "@type": "PropertyValue", "propertyID": "DOI", "value": str(item["doi"]),
            }
        if item.get("aw"):
            node["award"] = item["aw"]
        nodes.append(node)
    return nodes


def defined_terms_node(terms: list[dict]) -> dict:
    """DefinedTermSet com cada verbete do glossário (nome PT, nome EN e definição PT)."""
    set_id = URL + "/glossario.html#termset"
    ordered = sorted(terms, key=lambda term: alphabetical_key(term["pt"]["name"]))
    return {
        "@type": "DefinedTermSet",
        "@id": set_id,
        "name": "Glossário de química · Chemistry glossary",
        "url": URL + "/glossario.html",
        "inLanguage": ["pt-BR", "en"],
        "hasDefinedTerm": [{
            "@type": "DefinedTerm",
            "@id": f"{URL}/glossario.html#{term['id']}",
            "name": term["pt"]["name"],
            "alternateName": term["en"]["name"],
            "description": term["pt"]["definition"],
            "url": f"{URL}/glossario.html#{term['id']}",
            "inDefinedTermSet": {"@id": set_id},
        } for term in ordered],
    }


def metadata(
    path: str = "/",
    title: str = HOME_TITLE,
    description: str = HOME_DESCRIPTION,
    graph: list[dict] | None = None,
    og_title: str | None = None,
) -> str:
    """Cabeçalho comum: ícones, tema, CSP, Open Graph, estilo, fontes e JSON-LD."""
    graph = graph if graph is not None else [website_node(), person_node()]
    ld = {"@context": "https://schema.org", "@graph": graph}
    description = html.escape(description, quote=True)
    title = html.escape(title, quote=True)
    og_title = html.escape(og_title, quote=True) if og_title else title
    preloads = "\n".join(
        f'<link rel="preload" href="/assets/fonts/{name}" as="font" type="font/woff2" crossorigin>'
        for name in PRELOAD_FONTS
    )
    return f'''<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{URL}{path}">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" content="#f6f4ef" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#10161e" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:locale:alternate" content="en_US">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{URL}{path}">
<meta property="og:image" content="{URL}/assets/og.png">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{OG_ALT}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{URL}/assets/og.png">
<meta name="twitter:image:alt" content="{OG_ALT}">
{preloads}
<link rel="stylesheet" href="{asset("site.css")}">
<script type="application/ld+json">{json_for_html(ld)}</script>'''


def script_tags(*names: str) -> str:
    """Scripts externos adiados (executam em ordem depois da análise do HTML)."""
    return "\n".join(f'<script defer src="{asset(name)}"></script>' for name in names)


def inline_scripts(*names: str) -> str:
    """Somente para a prévia local, que não carrega arquivos relativos."""
    return "\n".join(
        f"<script>{(ROOT / 'assets' / name).read_text(encoding='utf-8')}</script>"
        for name in names
    )


def lastmod(*paths: str) -> str:
    """Data (AAAA-MM-DD) da última alteração das fontes: commit, ou hoje se houver edição pendente."""
    try:
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", *paths],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        if not dirty:
            out = subprocess.run(
                ["git", "log", "-1", "--format=%cs", "--", *paths],
                cwd=ROOT, capture_output=True, text=True, check=True,
            ).stdout.strip()
            if out:
                return out
    except (OSError, subprocess.CalledProcessError):
        pass
    return date.today().isoformat()


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


def render_glossary_page(body: str, content: str, terms: list[dict]) -> str:
    """Reutiliza estilo, navegação, rodapé e controles da página principal."""
    navigation = re.search(r'<nav class="nav".*?</nav>', body, re.S).group()
    navigation = re.sub(r'href="#([^"]+)"', r'href="index.html#\1"', navigation)
    navigation = navigation.replace(
        'href="glossario.html"', 'href="glossario.html" aria-current="page"'
    )
    footer = re.search(r"<footer>.*?</footer>", body, re.S).group()
    template = (ROOT / "src/glossario.html").read_text(encoding="utf-8")
    template = template.replace("{{GLOSSARIO_HTML}}", content)
    count = len(terms)
    title = f"Glossário de química ({count} termos) | Chemistry glossary · {SITE_NAME}"
    description = (
        f"Glossário bilíngue com {count} termos de química computacional, estados de "
        "transição, cinética, métodos analíticos e degradação de fármacos, com busca e "
        f"índice A–Z. / Bilingual glossary with {count} terms on computational chemistry, "
        "transition states, kinetics, analytical methods and drug degradation."
    )
    graph = [website_node(), person_node(), defined_terms_node(terms)]
    return (
        '<!doctype html>\n<html lang="pt-BR" data-lang="pt"><head>\n'
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
        + metadata("/glossario.html", title, description, graph)
        + '</head><body><a class="skip-link" href="#conteudo">'
        '<span lang="pt">Pular para o conteúdo</span><span lang="en">Skip to content</span></a>'
        + navigation + template + footer
        + "\n" + script_tags("site.js", "glossario.js")
        + '</body></html>\n'
    )


def render_sitemap() -> str:
    pages = (
        ("/", lastmod("src/body.html", "src/publicacoes.json", "assets/site.css")),
        ("/glossario.html", lastmod("src/glossario.json", "src/glossario.html")),
    )
    rows = "\n".join(
        f"  <url><loc>{URL}{path}</loc><lastmod>{mod}</lastmod></url>" for path, mod in pages
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}\n</urlset>\n"
    )


def main() -> None:
    """Atualiza a página, a 404 e um diretório de publicação sem fontes internas."""
    body = (ROOT / "src/body.html").read_text(encoding="utf-8")
    terms = json.loads((ROOT / "src/glossario.json").read_text(encoding="utf-8"))
    glossary = render_glossary(terms)
    items = json.loads((ROOT / "src/publicacoes.json").read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise ValueError("src/publicacoes.json deve conter uma lista.")
    body = body.replace("{{PUBLICACOES_HTML}}", render_publications(items))
    body = body.replace("{{PUBLICACOES_JSON}}", json_for_html(items))
    body = body.replace("{{DIPIRONA_JSON}}", (ROOT / "src/dipirona.json").read_text(encoding="utf-8").strip())
    page_body = body.replace("{{SCRIPTS}}", script_tags("site.js", "pubs.js", "mol.js"))
    if re.search(r"\{\{[A-Z_]+\}\}", page_body):
        raise ValueError("Existe um marcador de build sem substituição.")
    graph = [website_node(), person_node(), *publication_nodes(items)]
    document = (
        '<!doctype html>\n<html lang="pt-BR" data-lang="pt">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
        + metadata("/", HOME_TITLE, HOME_DESCRIPTION, graph)
        + "\n</head>\n<body>\n" + page_body + "\n</body>\n</html>\n"
    )
    # Site publicado: sem a faixa de prévia nem as marcações "confirmar" (ficam só em _preview.html)
    document = re.sub(r'<div class="preview" id="previewbar">.*?</div>\s*', "", document, count=1, flags=re.S)
    document = re.sub(r'\s*<span class="pend">[^<]*</span>', "", document)
    (ROOT / "index.html").write_text(document, encoding="utf-8")
    (ROOT / "glossario.html").write_text(
        render_glossary_page(body, glossary, terms), encoding="utf-8"
    )
    # Prévia no Claude: imagens, estilo e scripts embutidos (a página não carrega arquivos relativos)
    import base64
    def inline(m):
        f = ROOT / m.group(1)
        mime = "image/svg+xml" if f.suffix == ".svg" else "image/png" if f.suffix == ".png" else "image/jpeg"
        return 'src="data:%s;base64,%s"' % (mime, base64.b64encode(f.read_bytes()).decode())
    css = (ROOT / "assets/site.css").read_text(encoding="utf-8")
    preview_body = body.replace("{{SCRIPTS}}", inline_scripts("site.js", "pubs.js", "mol.js"))
    preview_body = preview_body.replace("</main>", glossary + "\n</main>", 1)
    preview_body = preview_body.replace("glossario.html#", "#").replace(
        'href="glossario.html"', 'href="#glossario"'
    )
    preview_body += inline_scripts("glossario.js")
    preview_document = (
        '<!doctype html><html lang="pt-BR" data-lang="pt"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{html.escape(HOME_TITLE)}</title><style>{css}</style></head><body>"
        + preview_body + '</body></html>'
    )
    (ROOT / "_preview.html").write_text(
        re.sub(r'src="(assets/[^"]+)"', inline, preview_document), encoding="utf-8"
    )
    error_page = f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<title>Página não encontrada · {SITE_NAME}</title>
<meta name="robots" content="noindex">
<meta name="theme-color" content="#f6f4ef" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#10161e" media="(prefers-color-scheme: dark)">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{asset("site.css")}">
</head><body><header class="hero"><div class="wrap"><div>
<a class="brand" href="/">O Meu Lab<b>‡</b></a>
<h1>404 · Página não encontrada</h1>
<p class="lead">O endereço pode ter mudado. Volte à página inicial para continuar.</p>
<p lang="en">Page not found. Return to the homepage to continue.</p>
<a class="btn primary" href="/">Voltar ao início</a>
</div></div></header></body></html>
'''
    (ROOT / "404.html").write_text(error_page, encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(render_sitemap(), encoding="utf-8")
    target = ROOT / "_site"
    target.mkdir(exist_ok=True)
    for name in (
        "index.html", "glossario.html", "404.html", "CNAME", ".nojekyll",
        "sitemap.xml", "robots.txt", *ROOT_FILES,
    ):
        shutil.copyfile(ROOT / name, target / name)
    shutil.rmtree(target / "assets", ignore_errors=True)
    for f in (ROOT / "assets").rglob("*"):
        if f.is_file() and f.suffix in ASSET_SUFFIXES:
            destination = target / "assets" / f.relative_to(ROOT / "assets")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, destination)
    print(
        f"Build concluído: {len(items)} publicações e {len(terms)} termos; "
        "saída em index.html, glossario.html e _site/."
    )


if __name__ == "__main__":
    main()
