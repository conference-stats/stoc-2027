const fs = require("node:fs");
const path = require("node:path");
const [engine, destination, indexPath = path.join(__dirname, "index.json")] = process.argv.slice(2);
const katex = require(path.resolve(engine));
const notation = JSON.parse(fs.readFileSync(path.join(__dirname, "math-notation.json"), "utf8"));
const input = fs.readFileSync(indexPath, "utf8");
const embedded = path.extname(indexPath) === ".html"
  ? input.match(/<script type="application\/json" id="data">([\s\S]*?)<\/script>/)
  : null;
if (path.extname(indexPath) === ".html" && !embedded) {
  throw new Error("Report is missing the embedded paper catalog");
}
const papers = JSON.parse(embedded ? embedded[1] : input);
const explicit = String.raw`\\\(((?:[^\\]|\\(?!\)))+)\\\)|(?<![\\$])\$((?:\\.|[^\\$\n])+)\$(?!\$)`;
const expressions = new Set(Object.values(notation));
for (const {title} of papers) {
  for (const match of title.matchAll(new RegExp(explicit, "g"))) expressions.add(match[1] ?? match[2]);
}
const mathml = Object.create(null);
for (const expression of [...expressions].sort()) {
  try {
    mathml[expression] = katex.renderToString(expression, {
      output: "mathml", trust: false, strict: "ignore", maxSize: 12, maxExpand: 150,
      macros: {"\\eps": "\\varepsilon", "\\Tilde": "\\widetilde"}
    }).replace(/<annotation\b[^>]*>[\s\S]*?<\/annotation>/g, "");
  } catch (error) {
    if (!(error instanceof katex.ParseError)) throw error;
    process.stderr.write(`TeX could not be rendered: ${expression}\n`);
  }
}
const data = JSON.stringify({explicit, notation, mathml});
const runtime = fs.readFileSync(path.join(__dirname, "math-runtime.js"), "utf8");
fs.writeFileSync(destination, `(() => {\nconst mathData = ${data};\n${runtime}\n})();\n`);
process.stdout.write(`Compiled ${Object.keys(mathml).length} of ${expressions.size} distinct formulas.\n`);
