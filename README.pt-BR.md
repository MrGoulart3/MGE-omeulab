# O Meu Laboratório

[English](README.md) · **Português brasileiro**

Site estático bilíngue. Fonte em `src/body.html`; publicações em
`src/publicacoes.json`. Requer Python 3.12 e Node 24 para validação; nenhuma
dependência Python externa.

```sh
python3 build.py
python3 -m unittest discover -s tests -v
node --test --test-isolation=none tests/site_runtime.test.cjs
```

Abra `index.html` localmente. `_site/` contém apenas os arquivos públicos para
Pages. `_preview.html` é uma prévia local gerada e ignorada pelo Git.

A sincronização ORCID é manual e exige o iD real informado pelo autor:

```sh
python3 scripts/orcid_sync.py "$ORCID_ID"
python3 build.py
```

Nenhum ORCID foi presumido. O script preserva a semente e a curadoria, concilia
DOI/título e não importa contatos ou biografia. Novos registros podem precisar
de autoria e categoria revisadas.

Publicação, DNS e conteúdo pendente: [próximos passos](docs/PROXIMOS_PASSOS.md).
O workflow Pages só inicia manualmente; a opção de publicar vem desmarcada.
