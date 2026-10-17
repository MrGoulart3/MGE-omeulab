# Próximos passos — O Meu Laboratório

Preparação local em 13/10/2026. O repositório continua na `main`, sem remote.
Nenhuma conta, configuração DNS ou publicação foi alterada.

## O que está pronto

- `CNAME` com `omeulab.com`, `.nojekyll`, favicon ‡ e página 404 no mesmo visual.
- Canonical, Open Graph, Twitter Card e JSON-LD `Person`, somente com o nome e
  os perfis que já constavam da página. Não há ORCID ou perfis presumidos.
- Sitemap de uma página e robots. A 404 tem `noindex`.
- Menu móvel com botão, estado ARIA, Escape, foco na seção escolhida e links
  acessíveis também sem JavaScript; link para pular ao conteúdo, foco visível,
  correção do atributo `hidden` nos filtros e suporte à redução de movimento.
- Cores de texto ajustadas e fontes do sistema. A imagem existente agora usa
  cache como arquivo, dimensões explícitas e carregamento adiado.
- Os 11 itens originais estão em `src/publicacoes.json`; o build embute o JSON
  e gera referências estáticas, legíveis sem JavaScript.
- `_site/` é um artefato local ignorado, contendo só oito arquivos públicos.
  O workflow manual envia somente essa pasta; não envia fontes, testes ou docs.

## DNS no Squarespace Domains

No painel **Domains**, abra `omeulab.com`, depois **DNS → DNS Settings → Custom
records → Add record**. O Squarespace documenta o apontamento de domínios para
serviços externos em [Pointing a Squarespace domain](https://support.squarespace.com/hc/en-us/articles/215744668-Pointing-a-Squarespace-domain).
Salve uma cópia da zona atual; substitua apenas registros de hospedagem que
conflitem com `@` ou `www`, preservando e-mail e verificações existentes.

Os destinos abaixo vêm da [documentação oficial de domínio próprio do GitHub
Pages](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site).

| Tipo | Host | Valor |
| --- | --- | --- |
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| AAAA | @ | 2606:50c0:8000::153 |
| AAAA | @ | 2606:50c0:8001::153 |
| AAAA | @ | 2606:50c0:8002::153 |
| AAAA | @ | 2606:50c0:8003::153 |
| CNAME | www | MrGoulart3.github.io |

O destino de `www` pressupõe publicação pela conta GitHub já vinculada na
página; se usar outra conta, substitua pelo respectivo `<usuario>.github.io`.
Não acrescente nome do repositório nem protocolo. Use o TTL padrão. Os AAAA
são opcionais; se usar IPv6, mantenha também os A. Não use wildcard `*`.

Antes de apontar os registros de hospedagem, verifique o domínio nas
configurações **da conta GitHub → Pages**, usando o TXT fornecido pelo GitHub;
conserve esse TXT. Cadastre também `omeulab.com` no **Custom domain** do
repositório. [Verificação oficial de domínio](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages).

## Checklist de publicação pelo Mario

1. Revisar todo conteúdo marcado como pendente abaixo e os arquivos gerados.
2. Escolher/criar o repositório de hospedagem e conectar o remote manualmente
   quando decidir publicar. Confirmar que o plano permite Pages na visibilidade
   escolhida. Essas ações não foram executadas.
3. Preferir **Settings → Pages → Source: GitHub Actions** e o workflow já
   preparado. Ele só inicia por **Run workflow**; `publicar` é falso por padrão.
   Primeiro executar sem publicação para revisar testes e artefato. Depois,
   na `main`, executar com `publicar` marcado para publicar deliberadamente.
   [Workflows oficiais do Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
4. Verificar a propriedade do domínio e salvar `omeulab.com` em **Custom domain**;
   configurar o DNS acima. Em workflows Actions, o campo do domínio é necessário
   mesmo com `CNAME` no artefato.
5. Aguardar a propagação e a emissão do certificado; ativar **Enforce HTTPS**
   quando disponível. Conferir os domínios raiz e `www` e o redirecionamento.
6. Após publicação, conferir a 404 em um caminho inexistente, favicon, metatags,
   sitemap, links e visualização móvel nos dois idiomas e temas.
7. Se optar por publicar direto da branch, selecionar `main / (root)` e manter
   `index.html` e `404.html` atualizados com o build. Essa modalidade publica
   também outros arquivos da raiz; o workflow com `_site/` reduz a exposição.

Consultas DNS para executar somente na fase de publicação:

```sh
dig omeulab.com A +short
dig omeulab.com AAAA +short
dig www.omeulab.com CNAME +short
```

## Publicações e ORCID

Nenhum iD foi criado ou atribuído ao autor. Quando tiver o iD real, forneça-o
como argumento, ou defina a variável local abaixo com o valor confirmado:

```sh
python3 scripts/orcid_sync.py "$ORCID_ID"
python3 build.py
python3 -m unittest discover -s tests -v
node --test --test-isolation=none tests/site_runtime.test.cjs
```

O sincronizador usa a biblioteca padrão e o endpoint público de obras da
[API ORCID](https://info.orcid.org/documentation/api-tutorials/api-tutorial-read-data-on-a-record/).
Valida o dígito verificador, usa timeout, escolhe o resumo preferido de cada
grupo, concilia DOI/título e preserva textos, autores e prêmios curados. Falhas
não substituem o arquivo. Nenhuma consulta à API foi feita nesta preparação.

Os resumos nem sempre trazem autoria; o script deixa esse campo vazio para
revisão, sem inventar nomes. Itens ausentes do ORCID continuam preservados;
remoções e correções bibliográficas são manuais. A importação não valida o
mérito científico, a autoria ou a completude da lista. Revise o diff antes de
um novo build. A rotina não altera o perfil/link ORCID na página automaticamente.

## Conteúdo que ainda precisa de confirmação

- ORCID real e links reais de Scholar, LinkedIn e ResearchGate, se desejar.
- Link Lattes já presente, categoria do prêmio de 2026 e o que pode ser divulgado
  sobre projetos de pesquisa em andamento.
- Datas de mestrado, graduação e experiência profissional marcadas como pendentes.
- Dados bibliográficos e premiações preservados da semente, antes da publicação.
- A imagem social (`assets/og.png`, 1200 × 630) é gerada por `scripts/make_images.py`
  (nome, linha de atuação e a molécula do site); revise o texto antes de publicar.
- A barra de prévia e as marcações permanecem até a revisão editorial. Ocultar
  marcações pelo botão não elimina as informações pendentes do HTML público.

## Validação local e limites

`python3 build.py` e 12 testes unittest passaram; cinco testes Node executaram
menu, Escape, foco, mudança de largura, idioma e filtros em DOM simulado. Cada
script extraído de `index.html` passou em `node --check`; os blocos JSON foram
parseados. A prévia não carrega fontes, bibliotecas ou recursos remotos.

Foram conferidas 12 combinações de texto/fundo: contraste mínimo 5,01:1 no tema
claro e 5,47:1 no escuro. Bordas de controles foram escurecidas para atingir
3:1 nos fundos claros. Isso não substitui uma auditoria WCAG completa.
Ainda falta inspeção visual em navegador real, teclado/leitor de tela e
validação do ambiente GitHub Pages, certificado e DNS após publicar.

## Melhorias de 17/10/2026 (branch `melhorias-2026-10-17`, sem publicação)

- Fontes autohospedadas (Fraunces variável opsz/wght, IBM Plex Sans 400/600, Plex Mono
  500/600; WOFF2 latin + latin-ext, licença OFL em `assets/fonts`), `font-display:swap`,
  preload só de Fraunces e Plex Sans 400. O ‡ do logo não existe nessas fontes e usa a
  serifa do sistema (como antes).
- og:image 1200×630, `twitter:card=summary_large_image`, favicon.ico, apple-touch-icon,
  manifest, `theme-color` claro/escuro. Imagens derivadas: `python3 scripts/make_images.py`.
- JSON-LD: `WebSite`, `Person` completo, `ScholarlyArticle` por publicação (home) e
  `DefinedTermSet`/`DefinedTerm` (glossário), gerados no build.
- CSS e JS externos em `assets/` (com `?v=hash`), sem `style=` nem script inline; CSP por
  `<meta>` sem `unsafe-inline`/`unsafe-eval` (o 3Dmol 2.5.5 funciona assim; vem do jsDelivr
  com SRI). `frame-ancestors` e `report-uri` não funcionam em `<meta>`.
- 3Dmol carregado sem bloquear (script injetado por `assets/mol.js`); a dipirona continua
  girando sempre e volta a girar depois de arrastar; se o 3Dmol falhar, usa o canvas próprio.
- Imagens em WebP (`<picture>`, jpg de reserva), `width`/`height`, `loading="lazy"` abaixo
  da dobra. Os recortes de altura fixa (galeria e cartão) seguem com `object-fit:cover`.
- Sitemap com `lastmod` (data do último commit das fontes; hoje se houver edição pendente).

Próximos passos sugeridos (não feitos):

- Rotas `/en/` e `/en/glossario.html` geradas no build, com `hreflang` + `x-default`
  e sitemap com `xhtml:link` (hoje o título e a descrição são bilíngues numa única URL).
- Estética: cartões em lista tipográfica (Pesquisa/Cultura), hero mais compacto,
  cabeçalho móvel menor, rótulos mono de 12 px (ESTÉTICA-2 a 4 do relatório).
- Conteúdo: promessa "novos vídeos a caminho", datas pendentes da trajetória, e-mail
  ofuscado, ORCID real.
- Opcional: autohospedar o 3Dmol (permitiria `script-src 'self'`).
