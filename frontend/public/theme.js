/* Executado antes da interface, sem script inline ou credenciais. */
(function () {
  const key = "loadx.appearance";
  const query = window.matchMedia("(prefers-color-scheme: dark)");
  const listeners = new Set();
  const valid = (value) => ["light", "dark", "system"].includes(value);
  let preference = "system";
  try {
    const saved = window.localStorage.getItem(key);
    if (valid(saved)) preference = saved;
  } catch { /* A preferência continua disponível em memória. */ }
  function apply() {
    document.documentElement.dataset.theme = preference === "system"
      ? (query.matches ? "dark" : "light") : preference;
    listeners.forEach((listener) => listener());
  }
  window.loadxTheme = {
    preference: () => preference,
    dark: () => document.documentElement.dataset.theme === "dark",
    set(value) {
      if (!valid(value)) return;
      preference = value;
      try { window.localStorage.setItem(key, value); } catch { /* Memória apenas. */ }
      apply();
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
  query.addEventListener("change", apply);
  window.addEventListener("storage", (event) => {
    if (event.key === key || event.key === null) {
      preference = valid(event.newValue) ? event.newValue : "system";
      apply();
    }
  });
  apply();
})();
