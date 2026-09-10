/* Build a library's public modules into a tree the page can share through an import map.
 *
 * A library that registers global custom element names cannot load twice on a page, so this
 * package serves one copy under the library's own bare specifiers (`imports` in the Python
 * package): another library on the page that imports it by name gets this copy instead of
 * registering the same tags a second time. The library publishes no build that can be served as-is
 * -- its modules import their dependencies by name -- so this builds one. Every module its
 * package.json "exports" names becomes an entry, written where that export points, and esbuild's
 * code splitting moves what the entries share into chunks, so each module exists once whichever
 * entry the page reaches it through.
 *
 * `patches` replaces the source of a module, keyed by `<package>/<file>`, for the rare published
 * module whose code does not match its own types. Returns the import map entries,
 * `{specifier: path under the vendor directory}`.
 */
import esbuild from "esbuild";
import fs from "fs";
import path from "path";

const CONDITIONS = ["browser", "import", "module", "default"];
const SCRIPT = /\.m?js$/;

/** The JS file an "exports" value points at, preferring browser/import conditions. */
function exportTarget(value) {
  if (typeof value === "string") return value;
  if (Array.isArray(value))
    return value.map(exportTarget).find(Boolean) ?? null;
  for (const condition of CONDITIONS) {
    if (value && condition in value) return exportTarget(value[condition]);
  }
  return null;
}

function filesUnder(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .flatMap((entry) =>
      entry.isDirectory()
        ? filesUnder(path.join(dir, entry.name))
        : [path.join(dir, entry.name)],
    );
}

/** Every script export of `name`: [specifier, file relative to the package] pairs. */
function publicModules(name) {
  const root = path.resolve("node_modules", name);
  const { exports: map = {} } = JSON.parse(
    fs.readFileSync(path.join(root, "package.json"), "utf8"),
  );
  const modules = [];
  const prefixes = [];
  for (const [key, value] of Object.entries(map)) {
    const target = exportTarget(value)?.replace(/^\.\//, "");
    if (!target) continue;
    const specifier = `${name}${key.slice(1)}`;
    if (!key.includes("*")) {
      if (SCRIPT.test(target)) modules.push([specifier, target]);
      continue;
    }
    const [keyHead, keyTail] = key.slice(2).split("*");
    const [head, tail] = target.split("*");
    for (const file of filesUnder(path.join(root, head))) {
      const rel = path.relative(root, file).split(path.sep).join("/");
      if (!rel.startsWith(head) || !rel.endsWith(tail) || !SCRIPT.test(rel))
        continue;
      if (rel.endsWith(".d.ts")) continue;
      const match = rel.slice(head.length, rel.length - tail.length);
      if (!match) continue; // `dist/index.js` against `dist/*/index.js`: no subpath at all
      modules.push([`${name}/${keyHead}${match}${keyTail}`, rel]);
    }
    // a pattern whose key and target end alike maps as one prefix rather than file by file
    if (keyTail === tail) prefixes.push([`${name}/${keyHead}`, head]);
  }
  return { root, modules, prefixes };
}

export async function vendor(names, outdir, patches = {}) {
  const entryPoints = {};
  const imports = {};
  for (const name of names) {
    const { root, modules, prefixes } = publicModules(name);
    for (const [specifier, rel] of modules) {
      entryPoints[`${name}/${rel.replace(SCRIPT, "")}`] = path.join(root, rel);
      imports[specifier] = `${name}/${rel.replace(SCRIPT, ".js")}`;
    }
    for (const [specifier, head] of prefixes) {
      // the prefix covers the exact entries that would resolve the same way; one it would resolve
      // differently (`./*.js` onto `*/define.js` under a `./*/` prefix) has to stay
      const target = `${name}/${head}`;
      for (const [key, value] of Object.entries(imports)) {
        if (
          key.startsWith(specifier) &&
          value === target + key.slice(specifier.length)
        )
          delete imports[key];
      }
      imports[specifier] = target;
    }
  }
  await esbuild.build({
    entryPoints,
    outdir,
    bundle: true,
    splitting: true,
    format: "esm",
    target: ["es2022"],
    minify: true,
    chunkNames: "chunks/[name]-[hash]",
    logLevel: "warning",
    plugins: [
      {
        name: "patches",
        setup(build) {
          build.onLoad({ filter: SCRIPT }, (args) => {
            const file = args.path.split(path.sep).join("/");
            const key = Object.keys(patches).find((k) =>
              file.endsWith(`/node_modules/${k}`),
            );
            return key ? { contents: patches[key], loader: "js" } : undefined;
          });
        },
      },
    ],
  });
  return imports;
}
