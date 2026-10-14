'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const data = JSON.parse(html.match(/<script id="publicacoes-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
function scripts(page) {
  return [...page.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)]
    .filter(match => !match[1].includes('type=')).map(match => match[2]);
}
const indexScripts = scripts(html);
const glossaryHTML = fs.readFileSync(path.join(__dirname, '..', 'glossario.html'), 'utf8');
const glossaryScripts = scripts(glossaryHTML);

class Element {
  constructor(dataset = {}, attributes = {}) {
    this.dataset = dataset;
    this.attributes = attributes;
    this.listeners = new Map();
    this.classes = new Set();
    this.children = [];
    this.value = '';
    this.classList = {
      add: value => this.classes.add(value),
      toggle: value => this.classes.has(value) ? this.classes.delete(value) : this.classes.add(value),
    };
  }
  setAttribute(key, value) {
    this.attributes[key] = value;
    if (key === 'data-lang') this.dataset.lang = value;
    if (key === 'data-theme') this.dataset.theme = value;
  }
  getAttribute(key) { return this.attributes[key]; }
  addEventListener(event, callback) {
    const handlers = this.listeners.get(event) || [];
    handlers.push(callback);
    this.listeners.set(event, handlers);
  }
  fire(event, payload = {}) {
    for (const callback of this.listeners.get(event) || []) callback(payload);
  }
  focus() { this.focused = true; }
  scrollIntoView() { this.scrolled = true; }
  appendChild(child) {
    if (child.parentNode) {
      child.parentNode.children = child.parentNode.children.filter(item => item !== child);
    }
    this.children.push(child);
    child.parentNode = this;
  }
}

function fixture(narrow = true, storedLanguage = null) {
  const root = new Element();
  const menu = new Element({}, {'aria-expanded': 'false'});
  const links = new Element();
  const anchor = new Element({}, {href: '#pesquisa'});
  const target = new Element();
  const theme = new Element();
  const items = data.map(item => new Element({k: item.k}));
  const list = new Element();
  list.querySelectorAll = () => items;
  links.querySelectorAll = () => [anchor];
  const languages = ['pt', 'en'].map(setlang => new Element({setlang}));
  const filters = ['all', 'art', 'pre', 'cong'].map(f => new Element({f}));
  const pending = new Element();
  const width = new Element();
  width.matches = narrow;
  const dark = new Element();
  dark.matches = false;
  const document = new Element();
  document.documentElement = root;
  document.querySelector = selector => ({'.menu-toggle': menu, '#pesquisa': target})[selector];
  document.getElementById = id => ({
    'nav-links': links, pubs: list, togglepend: pending, pesquisa: target,
    'theme-toggle': theme,
    'publicacoes-data': {textContent: JSON.stringify(data)},
  })[id];
  document.querySelectorAll = selector => ({
    '[data-setlang]': languages, '[data-f]': filters, '[data-copy]': [],
  })[selector];
  const stored = new Map(storedLanguage ? [['oml_lang', storedLanguage]] : []);
  const context = {
    document, matchMedia: query => query.includes('prefers-color-scheme') ? dark : width,
    navigator: {language: 'pt-BR'},
    localStorage: {getItem: key => stored.get(key), setItem: (key, value) => stored.set(key, value)},
  };
  indexScripts.slice(0, 2).forEach(script => {
    vm.runInNewContext(script, context, {filename: 'index.inline.js', timeout: 1000});
  });
  return {root, menu, links, anchor, target, items, languages, filters, pending, document, width, theme, stored};
}

test('o script inicia offline e o menu móvel responde a clique e Escape', () => {
  const f = fixture();
  assert.ok(f.root.classes.has('js'));
  assert.equal(f.menu.getAttribute('aria-expanded'), 'false');
  assert.equal(f.links.inert, true);
  f.menu.fire('click');
  assert.equal(f.menu.getAttribute('aria-expanded'), 'true');
  assert.equal(f.links.inert, false);
  f.document.fire('keydown', {key: 'Escape'});
  assert.equal(f.links.inert, true);
  assert.equal(f.menu.focused, true);
});

test('o link móvel fecha o menu e move o foco para a seção', () => {
  const f = fixture();
  f.menu.fire('click');
  f.anchor.fire('click');
  assert.equal(f.links.inert, true);
  assert.equal(f.target.focused, true);
  assert.equal(f.target.tabIndex, -1);
});

test('a navegação fica disponível ao mudar para desktop', () => {
  const f = fixture();
  f.width.matches = false;
  f.width.fire('change');
  assert.equal(f.links.inert, false);
  assert.equal(f.menu.getAttribute('aria-expanded'), 'false');
});

test('idioma, filtro e marcações funcionam sem erros de execução', () => {
  const f = fixture(false);
  assert.equal(f.root.lang, 'pt-BR');
  f.languages[1].fire('click');
  assert.equal(f.root.lang, 'en');
  assert.equal(f.languages[1].getAttribute('aria-pressed'), 'true');
  f.filters[1].fire('click');
  assert.equal(f.items.filter(item => !item.hidden).length, data.filter(item => item.k === 'art').length);
  f.filters[0].fire('click');
  assert.ok(f.items.every(item => item.hidden === false));
  f.pending.fire('click');
  assert.ok(f.root.classes.has('nopend'));
});

test('preferência de idioma inválida não oculta os dois idiomas', () => {
  assert.equal(fixture(false, 'invalid').root.lang, 'pt-BR');
});

test('o link para outra página fecha o menu móvel sem tratar a URL como seletor CSS', () => {
  const f = fixture();
  f.anchor.setAttribute('href', 'glossario.html');
  f.document.querySelector = () => { throw new Error('URL não é um seletor CSS'); };
  f.menu.fire('click');
  f.anchor.fire('click');
  assert.equal(f.links.inert, true);
});

test('o tema alterna entre claro e escuro e salva a preferência', () => {
  const f = fixture(false);
  assert.equal(f.theme.getAttribute('aria-pressed'), 'false');
  f.theme.fire('click');
  assert.equal(f.root.dataset.theme, 'dark');
  assert.equal(f.stored.get('oml_theme'), 'dark');
  assert.equal(f.theme.getAttribute('aria-pressed'), 'true');
  f.theme.fire('click');
  assert.equal(f.root.dataset.theme, 'light');
});

function decode(value) {
  return value.replace(/&quot;/g, '"').replace(/&#x27;/g, "'")
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}

function glossaryFixture(storedLanguage = 'pt', storedTheme = null, storageBlocked = false) {
  const root = new Element();
  const menu = new Element({}, {'aria-expanded': 'false'});
  const links = new Element();
  links.querySelectorAll = () => [];
  const languages = ['pt', 'en'].map(setlang => new Element({setlang}));
  const theme = new Element();
  const search = new Element();
  const status = new Element();
  const empty = new Element();
  const nodes = new Map([
    ['nav-links', links], ['theme-toggle', theme], ['glossary-search', search],
    ['glossary-status', status], ['glossary-empty', empty],
  ]);
  const groups = [...glossaryHTML.matchAll(/<section class="glossary-group" id="letter-([^"]+)"/g)]
    .map(match => {
      const group = new Element({glossaryLetter: match[1]});
      const container = new Element();
      group.querySelector = () => container;
      group.querySelectorAll = () => container.children;
      nodes.set('letter-' + match[1], group);
      return group;
    });
  const letters = groups.map(group => new Element({}, {href: '#letter-' + group.dataset.glossaryLetter}));
  const entries = [...glossaryHTML.matchAll(/<article class="card glossary-term" id="([^"]+)" data-pt="([^"]+)" data-en="([^"]+)">([\s\S]*?)<\/article>/g)]
    .map(match => {
      const entry = new Element({pt: decode(match[2]), en: decode(match[3])});
      entry.id = match[1];
      entry.textContent = decode(match[4].replace(/<[^>]*>/g, ' '));
      nodes.set(entry.id, entry);
      return entry;
    });
  const document = new Element();
  document.documentElement = root;
  document.querySelector = () => menu;
  document.getElementById = id => nodes.get(id);
  document.querySelectorAll = selector => ({
    '[data-setlang]': languages, '.glossary-term': entries,
    '[data-glossary-letter]': groups, '[data-letter-link]': letters,
  })[selector];
  const width = new Element();
  width.matches = true;
  const dark = new Element();
  dark.matches = false;
  const window = new Element();
  const location = {hash: ''};
  const stored = new Map([['oml_lang', storedLanguage]]);
  if (storedTheme) stored.set('oml_theme', storedTheme);
  const context = {
    document, window, location, navigator: {language: 'pt-BR'},
    matchMedia: query => query.includes('prefers-color-scheme') ? dark : width,
    localStorage: {
      getItem: key => { if (storageBlocked) throw new Error('blocked'); return stored.get(key); },
      setItem: (key, value) => { if (storageBlocked) throw new Error('blocked'); stored.set(key, value); },
    },
  };
  glossaryScripts.forEach(script => vm.runInNewContext(script, context, {timeout: 1000}));
  function query(value) { search.value = value; search.fire('input'); }
  return {root, menu, links, languages, theme, search, status, empty, groups, letters, entries, nodes, location, window, query};
}

test('o glossário filtra em tempo real sem distinguir acentos ou maiúsculas', () => {
  const f = glossaryFixture();
  f.query('  OZoNIO  ');
  assert.deepEqual(f.entries.filter(entry => !entry.hidden).map(entry => entry.id), ['ozonio', 'poa']);
  assert.equal(f.status.textContent, `2 de ${f.entries.length} termos`);
  f.query('OZÔNIO');
  assert.ok(!f.nodes.get('ozonio').hidden);
  f.query('NÃO_EXISTE_123');
  assert.ok(f.entries.every(entry => entry.hidden));
  assert.equal(f.empty.hidden, false);
  assert.ok(f.groups.every(group => group.hidden));
  assert.ok(f.letters.every(letter => letter.hidden));
  f.query('');
  assert.ok(f.entries.every(entry => !entry.hidden));
  assert.equal(f.empty.hidden, true);
});

test('a busca encontra siglas, nomes em inglês e palavras das definições', () => {
  const f = glossaryFixture();
  f.query('LDH');
  assert.ok(!f.nodes.get('hdl').hidden);
  f.query('ZERO-POINT');
  assert.ok(!f.nodes.get('energia-de-ponto-zero').hidden);
  f.query('bromato');
  assert.ok(!f.nodes.get('ozonio').hidden);
  f.query('Skodje');
  assert.ok(!f.nodes.get('skodje-truhlar').hidden);
});

test('idioma reorganiza o índice e os grupos, preservando busca e âncoras', () => {
  const f = glossaryFixture();
  const hdl = f.nodes.get('hdl');
  assert.ok(f.nodes.get('letter-H').querySelectorAll().includes(hdl));
  f.languages[1].fire('click');
  assert.equal(f.root.lang, 'en');
  assert.ok(f.nodes.get('letter-L').querySelectorAll().includes(hdl));
  assert.ok(!f.nodes.get('letter-L').hidden);
  assert.equal(f.status.textContent, `${f.entries.length} of ${f.entries.length} terms`);
  const grouped = f.groups.flatMap(group => group.querySelectorAll());
  assert.equal(grouped.length, f.entries.length);
  assert.equal(new Set(grouped).size, f.entries.length);
  f.query('ozonio');
  f.languages[0].fire('click');
  assert.equal(f.search.value, 'ozonio');
  assert.equal(f.status.textContent, `2 de ${f.entries.length} termos`);
  assert.ok(!f.nodes.get('ozonio').hidden);
  assert.deepEqual(f.letters.filter(letter => !letter.hidden).map(letter => letter.getAttribute('href')), ['#letter-O', '#letter-P']);
});

test('a página do glossário inicia com preferências salvas e sem armazenamento disponível', () => {
  const f = glossaryFixture('en', 'dark');
  assert.equal(f.root.lang, 'en');
  assert.equal(f.root.dataset.theme, 'dark');
  assert.equal(f.theme.getAttribute('aria-pressed'), 'true');
  assert.ok(f.nodes.get('letter-L').querySelectorAll().includes(f.nodes.get('hdl')));
  const blocked = glossaryFixture('en', null, true);
  assert.equal(blocked.root.lang, 'pt-BR');
  blocked.query('ozonio');
  assert.ok(!blocked.nodes.get('ozonio').hidden);
});

test('links diretos revelam verbetes ocultos pela busca', () => {
  const f = glossaryFixture();
  f.query('ozonio');
  assert.equal(f.nodes.get('dft').hidden, true);
  f.location.hash = '#dft';
  f.window.fire('hashchange');
  assert.equal(f.search.value, '');
  assert.equal(f.nodes.get('dft').hidden, false);
  assert.equal(f.nodes.get('dft').scrolled, true);
  f.location.hash = '#%malformado';
  assert.doesNotThrow(() => f.window.fire('hashchange'));
});

test('o site remove o podcast do autor e mantém links para o glossário', () => {
  for (const page of [html, glossaryHTML]) {
    assert.doesNotMatch(page, /at[oô]micos|anchor\.fm/i);
  }
  assert.ok(html.includes('Moléculas'));
  assert.match(html, /href="glossario\.html"/);
  assert.match(html, /href="glossario\.html#dft"/);
});
