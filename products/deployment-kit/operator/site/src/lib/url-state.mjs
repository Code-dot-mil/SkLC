export function readQueryValue(search, key, fallback, allowedValues) {
  const params = new URLSearchParams(normalizeSearch(search));
  const value = params.get(key);
  if (!value) {
    return fallback;
  }
  if (allowedValues && !allowedValues.includes(value)) {
    return fallback;
  }
  return value;
}

export function updateQueryString(search, updates, defaults = {}) {
  const params = new URLSearchParams(normalizeSearch(search));
  for (const [key, value] of Object.entries(updates)) {
    const nextValue = value == null ? "" : String(value);
    const defaultValue = defaults[key] == null ? "" : String(defaults[key]);
    if (!nextValue || nextValue === defaultValue) {
      params.delete(key);
    } else {
      params.set(key, nextValue);
    }
  }

  const next = params.toString();
  return next ? `?${next}` : "";
}

export function replaceQueryState(updates, defaults = {}, win = globalThis.window) {
  if (!win?.location || !win.history?.replaceState) {
    return;
  }
  const nextSearch = updateQueryString(win.location.search, updates, defaults);
  const nextUrl = `${win.location.pathname}${nextSearch}${win.location.hash}`;
  win.history.replaceState(win.history.state, "", nextUrl);
}

function normalizeSearch(search) {
  return search.startsWith("?") ? search.slice(1) : search;
}
