(function () {
  var root = document.documentElement;
  var search = document.getElementById('glossary-search');
  var status = document.getElementById('glossary-status');
  var empty = document.getElementById('glossary-empty');
  var entries = Array.from(document.querySelectorAll('.glossary-term'));
  var groups = Array.from(document.querySelectorAll('[data-glossary-letter]'));
  var letters = Array.from(document.querySelectorAll('[data-letter-link]'));
  function normalize(value) {
    return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }
  var searchable = new Map(entries.map(function (entry) {
    return [entry, normalize(entry.textContent)];
  }));
  function filter() {
    var query = normalize(search.value.trim());
    var count = 0;
    entries.forEach(function (entry) {
      entry.hidden = !searchable.get(entry).includes(query);
      if (!entry.hidden) count++;
    });
    groups.forEach(function (group) {
      group.hidden = !Array.from(group.querySelectorAll('.glossary-term')).some(function (entry) { return !entry.hidden; });
    });
    letters.forEach(function (link) {
      link.hidden = document.getElementById(link.getAttribute('href').slice(1)).hidden;
    });
    empty.hidden = count !== 0;
    status.textContent = root.dataset.lang === 'en'
      ? count + ' of ' + entries.length + ' terms'
      : count + ' de ' + entries.length + ' termos';
  }
  function regroup() {
    var language = root.dataset.lang === 'en' ? 'en' : 'pt';
    entries.sort(function (a, b) {
      return a.dataset[language].localeCompare(b.dataset[language], language, {sensitivity: 'base', numeric: true});
    });
    entries.forEach(function (entry) {
      var letter = normalize(entry.dataset[language]).charAt(0).toUpperCase();
      if (/\d/.test(letter)) letter = '0-9';
      document.getElementById('letter-' + letter).querySelector('.glossary-entries').appendChild(entry);
    });
    filter();
  }
  function revealHash() {
    var id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch (e) { return; }
    var target = document.getElementById(id);
    if (target && entries.includes(target) && target.hidden) {
      search.value = '';
      filter();
      target.scrollIntoView();
    }
  }
  search.addEventListener('input', filter);
  document.querySelectorAll('[data-setlang]').forEach(function (button) {
    button.addEventListener('click', regroup);
  });
  window.addEventListener('hashchange', revealHash);
  regroup();
  revealHash();
})();
