const {explicit, notation, mathml} = mathData;
const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const literals = Object.keys(notation).sort((a, b) => b.length - a.length);
const prosePattern = literals.map(escapeRegExp).join("|");
const template = document.createElement("template");

function typeset(element, value = element.textContent, prose = false) {
  const pattern = new RegExp(prose ? prosePattern : `${explicit}|${prosePattern}`, "g");
  const parts = document.createDocumentFragment();
  let start = 0;
  for (const match of value.matchAll(pattern)) {
    const formula = (prose ? undefined : match[1] ?? match[2]) ?? notation[match[0]];
    if (!Object.hasOwn(mathml, formula)) continue;
    parts.append(value.slice(start, match.index));
    template.innerHTML = mathml[formula];
    parts.append(template.content.cloneNode(true));
    start = match.index + match[0].length;
  }
  if (!start) {
    if (value !== element.textContent || element.childElementCount) element.textContent = value;
    return;
  }
  parts.append(value.slice(start));
  element.replaceChildren(parts);
}

window.reportMath = {typeset};
document.querySelectorAll("[data-tex-title]").forEach((title) => typeset(title));
