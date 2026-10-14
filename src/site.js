(function () {
  var root = document.documentElement;
  var menu = document.querySelector('.menu-toggle');
  var links = document.getElementById('nav-links');
  var narrow = matchMedia('(max-width:860px)');
  function setMenu(open) {
    menu.setAttribute('aria-expanded', String(open));
    links.dataset.open = String(open);
    links.inert = narrow.matches && !open;
  }
  menu.addEventListener('click', function () {
    setMenu(menu.getAttribute('aria-expanded') !== 'true');
  });
  links.querySelectorAll('a').forEach(function (a) {
    a.addEventListener('click', function () {
      if (!narrow.matches) return;
      setMenu(false);
      var href = a.getAttribute('href');
      if (href.charAt(0) !== '#') return;
      var target = document.getElementById(href.slice(1));
      if (target) { target.tabIndex = -1; target.focus({preventScroll: true}); }
    });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && narrow.matches && menu.getAttribute('aria-expanded') === 'true') {
      setMenu(false); menu.focus();
    }
  });
  narrow.addEventListener('change', function () { setMenu(false); });
  root.classList.add('js');
  setMenu(false);
  function store(key, value) {
    try {
      if (value === undefined) return localStorage.getItem(key);
      localStorage.setItem(key, value);
    } catch (e) { return null; }
  }
  function setLang(language) {
    language = language === 'en' ? 'en' : 'pt';
    root.setAttribute('data-lang', language);
    root.lang = language === 'en' ? 'en' : 'pt-BR';
    document.querySelectorAll('[data-setlang]').forEach(function (button) {
      button.setAttribute('aria-pressed', String(button.dataset.setlang === language));
    });
    store('oml_lang', language);
  }
  setLang(store('oml_lang') || ((navigator.language || 'pt').toLowerCase().indexOf('pt') === 0 ? 'pt' : 'en'));
  document.querySelectorAll('[data-setlang]').forEach(function (button) {
    button.addEventListener('click', function () { setLang(button.dataset.setlang); });
  });
  var theme = document.getElementById('theme-toggle');
  var dark = matchMedia('(prefers-color-scheme: dark)');
  var savedTheme = store('oml_theme');
  if (savedTheme === 'light' || savedTheme === 'dark') root.setAttribute('data-theme', savedTheme);
  function isDark() { return root.dataset.theme ? root.dataset.theme === 'dark' : dark.matches; }
  function updateTheme() { theme.setAttribute('aria-pressed', String(isDark())); }
  theme.addEventListener('click', function () {
    var value = isDark() ? 'light' : 'dark';
    root.setAttribute('data-theme', value);
    store('oml_theme', value);
    updateTheme();
  });
  dark.addEventListener('change', updateTheme);
  updateTheme();
})();
