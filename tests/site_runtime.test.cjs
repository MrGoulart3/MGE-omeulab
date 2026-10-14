'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const data = JSON.parse(html.match(/<script id="publicacoes-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const script = [...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)]
  .filter(match => !match[1].includes('type='))[0][2];

class Element {
  constructor(dataset = {}, attributes = {}) {
    this.dataset = dataset;
    this.attributes = attributes;
    this.listeners = new Map();
    this.classes = new Set();
    this.classList = {
      add: value => this.classes.add(value),
      toggle: value => this.classes.has(value) ? this.classes.delete(value) : this.classes.add(value),
    };
  }
  setAttribute(key, value) {
    this.attributes[key] = value;
    if (key === 'data-lang') this.dataset.lang = value;
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
}

function fixture(narrow = true, storedLanguage = null) {
  const root = new Element();
  const menu = new Element({}, {'aria-expanded': 'false'});
  const links = new Element();
  const anchor = new Element({}, {href: '#pesquisa'});
  const target = new Element();
  const items = data.map(item => new Element({k: item.k}));
  const list = new Element();
  list.querySelectorAll = () => items;
  links.querySelectorAll = () => [anchor];
  const languages = ['pt', 'en'].map(setlang => new Element({setlang}));
  const filters = ['all', 'art', 'pre', 'cong'].map(f => new Element({f}));
  const pending = new Element();
  const width = new Element();
  width.matches = narrow;
  const document = new Element();
  document.documentElement = root;
  document.querySelector = selector => ({'.menu-toggle': menu, '#pesquisa': target})[selector];
  document.getElementById = id => ({
    'nav-links': links, pubs: list, togglepend: pending,
    'publicacoes-data': {textContent: JSON.stringify(data)},
  })[id];
  document.querySelectorAll = selector => ({
    '[data-setlang]': languages, '[data-f]': filters, '[data-copy]': [],
  })[selector];
  const stored = new Map(storedLanguage ? [['oml_lang', storedLanguage]] : []);
  const context = {
    document, matchMedia: () => width, navigator: {language: 'pt-BR'},
    localStorage: {getItem: key => stored.get(key), setItem: (key, value) => stored.set(key, value)},
  };
  vm.runInNewContext(script, context, {filename: 'index.inline.js', timeout: 1000});
  return {root, menu, links, anchor, target, items, languages, filters, pending, document, width};
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
