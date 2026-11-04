(() => {
  const names = localeNames;
  const locales = Object.keys(names).sort();
  const countryCodes = {
    Australia:"AU", Austria:"AT", Bangladesh:"BD", Brazil:"BR", Bulgaria:"BG", Burundi:"BI",
    Canada:"CA", Chile:"CL", China:"CN", Czechia:"CZ", Denmark:"DK", Finland:"FI", France:"FR",
    Germany:"DE", Greece:"GR", Hungary:"HU", Iceland:"IS", India:"IN", Iran:"IR", Ireland:"IE",
    Israel:"IL", Italy:"IT", Japan:"JP", Malaysia:"MY", Mexico:"MX", Mongolia:"MN", Morocco:"MA",
    "New Zealand":"NZ", Norway:"NO", Poland:"PL", Portugal:"PT", Romania:"RO", Russia:"RU",
    Rwanda:"RW", "Saudi Arabia":"SA", Singapore:"SG", Slovakia:"SK", Slovenia:"SI", "South Korea":"KR",
    Spain:"ES", Sweden:"SE", Switzerland:"CH", Tajikistan:"TJ", Thailand:"TH", "The Netherlands":"NL",
    "Türkiye":"TR", "United Arab Emirates":"AE", "United Kingdom":"GB", "United States":"US",
    Uzbekistan:"UZ", Venezuela:"VE", Vietnam:"VN", Yemen:"YE"
  };
  const storageKey = "conference-stats-language";
  const dictionaries = localeMessages;
  const numeric = /(?<![\p{L}\d])\d+(?:[,.]\d+)*/gu;
  const countryNames = new Map();
  const textState = new WeakMap();
  const attributeState = new WeakMap();
  const attributes = ["aria-label", "placeholder", "title"];
  const excluded = "script, style, template, [translate=no], [data-math-prose]";
  const mathProse = [...document.querySelectorAll("[data-math-prose]")]
    .map((element) => [element, element.textContent]);
  const pageTitle = document.title;
  const description = document.querySelector('meta[name="description"]');
  const pageDescription = description?.content;
  let language = "en";
  try {
    const saved = sessionStorage.getItem(storageKey);
    if (locales.includes(saved)) language = saved;
  } catch {}
  function country(text, locale) {
    if (!Object.hasOwn(countryCodes, text)) return;
    if (!countryNames.has(locale)) {
      try { countryNames.set(locale, new Intl.DisplayNames([locale], {type:"region"})); }
      catch { countryNames.set(locale, null); }
    }
    return countryNames.get(locale)?.of(countryCodes[text]);
  }
  function translate(text, locale = language) {
    if (locale === "en") return text;
    const [full, lead, core, trail] = /^(\s*)([\s\S]*?)(\s*)$/.exec(text);
    if (!core) return full;
    const key = core.replace(/\s+/g, " ");
    const dict = dictionaries[locale];
    let result = Object.hasOwn(dict.text, key) ? dict.text[key] : country(key, locale);
    if (!result) {
      const values = [];
      const pattern = key.replace(numeric, (number) => `{${values.push(number) - 1}}`);
      const template = values.length && Object.hasOwn(dict.patterns, pattern) && dict.patterns[pattern];
      if (template) result = template.replace(/\{(\d+)\}/g, (_, index) => values[index] ?? "");
    }
    if (!result && key.includes(" · ")) result = key.split(" · ").map((piece) => translate(piece, locale)).join(" · ");
    return result ? lead + result + trail : text;
  }
  function updateText(node) {
    if (!node.parentElement || node.parentElement.closest(excluded)) return;
    const cached = textState.get(node);
    const original = cached && cached.rendered === node.data ? cached.original : node.data;
    const rendered = translate(original);
    textState.set(node, {original, rendered});
    if (rendered !== node.data) node.data = rendered;
  }
  function updateAttributes(element) {
    if (element.closest(excluded)) return;
    let cache = attributeState.get(element);
    for (const name of attributes) {
      if (!element.hasAttribute(name)) continue;
      if (!cache) {
        cache = {};
        attributeState.set(element, cache);
      }
      const value = element.getAttribute(name);
      const original = cache[name]?.rendered === value ? cache[name].original : value;
      const rendered = translate(original);
      cache[name] = {original, rendered};
      if (value !== rendered) element.setAttribute(name, rendered);
    }
  }
  function localize(node) {
    if (node.nodeType === Node.TEXT_NODE) return updateText(node);
    if (node.nodeType !== Node.ELEMENT_NODE || node.closest(excluded)) return;
    updateAttributes(node);
    const walker = document.createTreeWalker(node, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode(child) {
        return child.nodeType === Node.ELEMENT_NODE && child.matches(excluded)
          ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
      }
    });
    while (walker.nextNode()) {
      const child = walker.currentNode;
      if (child.nodeType === Node.TEXT_NODE) updateText(child);
      else updateAttributes(child);
    }
  }
  const observer = new MutationObserver((records) => {
    const roots = new Set();
    for (const record of records) {
      if (record.type === "attributes") updateAttributes(record.target);
      else if (record.type === "characterData") updateText(record.target);
      else for (const node of record.addedNodes) if (node.isConnected) roots.add(node);
    }
    for (const node of roots) if (!roots.has(node.parentNode)) localize(node);
  });
  const settings = {subtree:true, childList:true, characterData:true, attributes:true, attributeFilter:attributes};
  const languageControls = [];
  const themeKey = "conference-stats-theme";
  const themeButtons = [...document.querySelectorAll("[data-theme-option]")];
  function setTheme(theme) {
    const selected = theme === "glass" ? "glass" : "solid";
    document.documentElement.dataset.theme = selected;
    for (const button of themeButtons) {
      button.setAttribute("aria-pressed", String(button.dataset.themeOption === selected));
    }
    try { localStorage.setItem(themeKey, selected); } catch {}
  }
  let theme = "solid";
  try { theme = localStorage.getItem(themeKey) || "solid"; } catch {}
  setTheme(theme);
  for (const button of themeButtons) {
    button.addEventListener("click", () => setTheme(button.dataset.themeOption));
  }
  function apply(locale) {
    language = locale;
    document.documentElement.lang = locale === "zh" ? "zh-Hans" : locale;
    document.title = translate(pageTitle);
    if (description) description.content = translate(pageDescription);
    for (const {trigger, label, buttons} of languageControls) {
      label.textContent = names[locale];
      label.lang = document.documentElement.lang;
      trigger.setAttribute("aria-label", `Language · ${names[locale]}`);
      for (const button of buttons) button.setAttribute("aria-pressed", String(button.value === locale));
    }
    observer.disconnect();
    localize(document.body);
    for (const [element, source] of mathProse) {
      const translated = translate(source);
      if (window.reportMath) window.reportMath.typeset(element, translated, true);
      else element.textContent = translated;
    }
    observer.observe(document.body, settings);
    try { sessionStorage.setItem(storageKey, locale); } catch {}
    document.dispatchEvent(new Event("report:language"));
  }
  for (const control of document.querySelectorAll("[data-language-control]")) {
    const trigger = control.querySelector(".language-trigger");
    const label = control.querySelector(".language-trigger-label");
    const popover = control.querySelector(".language-popover");
    const buttons = locales.map((code) => {
      const button = document.createElement("button");
      button.type = "button";
      button.value = code;
      button.textContent = names[code];
      button.setAttribute("aria-label", names[code]);
      button.translate = false;
      button.lang = code === "zh" ? "zh-Hans" : code;
      button.addEventListener("click", () => {
        apply(code);
        setOpen(false);
        trigger.focus();
      });
      return button;
    });

    function setOpen(open) {
      popover.hidden = !open;
      trigger.setAttribute("aria-expanded", String(open));
    }

    trigger.addEventListener("click", () => setOpen(popover.hidden));
    control.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !popover.hidden) {
        event.preventDefault();
        setOpen(false);
        trigger.focus();
      }
      const offset = event.key === "ArrowDown" ? 1 : event.key === "ArrowUp" ? -1 : 0;
      if (offset) {
        event.preventDefault();
        const index = buttons.indexOf(document.activeElement);
        setOpen(true);
        const next = index < 0 ? locales.indexOf(language) : (index + offset + buttons.length) % buttons.length;
        buttons[next].focus();
      }
    });
    control.addEventListener("focusout", (event) => {
      if (!control.contains(event.relatedTarget)) setOpen(false);
    });
    document.addEventListener("pointerdown", (event) => {
      if (!control.contains(event.target)) setOpen(false);
    });
    popover.append(...buttons);
    control.hidden = false;
    languageControls.push({trigger, label, buttons});
  }
  window.reportI18n = {
    all(text) { return [...new Set(locales.map((locale) => translate(text, locale)))]; },
    original(element) {
      const node = element.firstChild;
      return (node && textState.get(node)?.original) || element.textContent;
    }
  };
  apply(language);
})();
