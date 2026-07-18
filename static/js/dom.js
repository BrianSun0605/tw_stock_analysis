export function byId(id) {
  return document.getElementById(id);
}

export function node(tag, options = {}, children = []) {
  const element = document.createElement(tag);
  for (const [key, value] of Object.entries(options)) {
    if (value === undefined || value === null) continue;
    if (key === "className") element.className = value;
    else if (key === "text") element.textContent = String(value);
    else if (key === "dataset") Object.assign(element.dataset, value);
    else if (key === "href") element.href = safeUrl(value) || "#";
    else element.setAttribute(key, String(value));
  }
  for (const child of Array.isArray(children) ? children : [children]) {
    if (child instanceof Node) element.append(child);
    else if (child !== undefined && child !== null) element.append(document.createTextNode(String(child)));
  }
  return element;
}

export function replace(id, children) {
  const target = byId(id);
  target.replaceChildren(...(Array.isArray(children) ? children : [children]));
  return target;
}

export function safeUrl(value) {
  try {
    const parsed = new URL(String(value), window.location.origin);
    return ["http:", "https:"].includes(parsed.protocol) ? parsed.href : null;
  } catch {
    return null;
  }
}

export function present(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

export function number(value, digits = 2) {
  if (!present(value)) return "資料不足";
  return new Intl.NumberFormat("zh-TW", { maximumFractionDigits: digits }).format(Number(value));
}

export function money(value, currency = true) {
  if (!present(value)) return "資料不足";
  return `${currency ? "NT$ " : ""}${number(value, 2)}`;
}

export function percentPoint(value, digits = 2) {
  return present(value) ? `${number(value, digits)}%` : "資料不足";
}

export function percentDecimal(value, digits = 2) {
  return present(value) ? `${number(Number(value) * 100, digits)}%` : "資料不足";
}

export function compactMoney(value) {
  if (!present(value)) return "資料不足";
  return new Intl.NumberFormat("zh-TW", { notation: "compact", maximumFractionDigits: 2 }).format(Number(value));
}
