/* The manifest the Python catalog is generated from.
 *
 * Collects the custom element declarations of the packages this package serves into one Custom
 * Elements Manifest, dropping everything else a published manifest carries (functions, variables,
 * icon data), and appends what an element inherits from a superclass or mixin in another package,
 * marked `inheritedFrom` -- a published manifest inlines inherited attributes only from within its
 * own package. A class that no manifest declares fails the run, so an upgrade that introduces one
 * cannot slip through; declarations a package leaves out can be supplied in tools/unpublished.json.
 * `make catalog` runs this and regenerates the Python classes.
 */
import fs from "fs";
import path from "path";

const PACKAGES = ["@blueprintui/components", "@blueprintui/icons"];
const OUT = "../spaday_blueprint/custom-elements.json";
// every element in the manifests registers itself when its module loads, so all are kept
const REGISTERED = null;
// tags a published manifest lists under names the package no longer registers
const RENAMED = {};

const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8"));
const UNPUBLISHED = fs.existsSync("tools/unpublished.json")
  ? readJson("tools/unpublished.json")
  : {};
// platform and Lit bases contribute nothing an author sets
const PLATFORM = new Set(["HTMLElement", "LitElement", "ReactiveElement"]);
const MERGED = ["attributes", "events", "slots"];

function packageName(spec) {
  const parts = spec.split("/");
  return parts.slice(0, spec.startsWith("@") ? 2 : 1).join("/");
}

/** The manifest of package `name` as resolved from `fromDir`, falling back to unpublished.json. */
function manifestOf(name, fromDir) {
  let dir = fs.realpathSync(fromDir);
  for (;;) {
    const pkgDir = path.join(dir, "node_modules", name);
    if (fs.existsSync(path.join(pkgDir, "package.json"))) {
      const { customElements = "custom-elements.json" } = readJson(
        path.join(pkgDir, "package.json"),
      );
      const file = path.join(pkgDir, customElements);
      if (fs.existsSync(file))
        return { manifest: readJson(file), dir: pkgDir, name };
      break; // named in package.json, never shipped
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return UNPUBLISHED[name]
    ? { manifest: UNPUBLISHED[name], dir: fromDir, name }
    : null;
}

function declaration(manifest, name) {
  for (const mod of manifest.modules ?? []) {
    for (const decl of mod.declarations ?? [])
      if (decl.name === name) return decl;
  }
  return null;
}

/** Where `name` is declared, starting at `source` and following re-exports into other packages. */
function locate(source, name) {
  const decl =
    declaration(source.manifest, name) ??
    declaration(UNPUBLISHED[source.name] ?? {}, name);
  if (decl) return { decl, source };
  for (const mod of source.manifest.modules ?? []) {
    for (const exported of mod.exports ?? []) {
      const target = exported.declaration;
      if (exported.name !== name || !target?.package) continue;
      const next = manifestOf(packageName(target.package), source.dir);
      if (next && next.name !== source.name) return locate(next, target.name);
    }
  }
  return null;
}

/** `decl`'s superclass and mixins from other packages, and theirs, nearest first. */
function ancestors(decl, owner, missing) {
  const found = [];
  for (const ref of [decl.superclass, ...(decl.mixins ?? [])]) {
    if (!ref?.package || PLATFORM.has(ref.name)) continue; // same-package ones are already inlined
    if (/^(lit|@lit\/)/.test(ref.package)) continue;
    const source = manifestOf(packageName(ref.package), owner.dir);
    const hit = source && locate(source, ref.name);
    if (!hit) {
      missing.add(`${ref.name} (${ref.package})`);
      continue;
    }
    found.push(
      {
        decl: hit.decl,
        from: { name: ref.name, package: hit.source.name },
      },
      ...ancestors(hit.decl, hit.source, missing),
    );
  }
  return found;
}

function resolve(decl, owner, missing) {
  const out = structuredClone(decl);
  out.tagName = RENAMED[decl.tagName] ?? decl.tagName;
  for (const key of MERGED) out[key] ??= [];
  for (const { decl: ancestor, from } of ancestors(decl, owner, missing)) {
    for (const key of MERGED) {
      const have = new Set(out[key].map((entry) => entry.name));
      for (const entry of ancestor[key] ?? []) {
        if (have.has(entry.name)) continue; // the nearer declaration wins
        out[key].push({ ...entry, inheritedFrom: entry.inheritedFrom ?? from });
        have.add(entry.name);
      }
    }
  }
  // Cleaned up after the merge, so what ancestors bring in is covered too. A slot published without
  // a name is the default slot, which the manifest schema spells "" (UI5 spells it "default"); an
  // event without one names nothing anyone can listen for.
  out.slots = out.slots.map((slot) => ({
    ...slot,
    name: slot.name === "default" ? "" : (slot.name ?? ""),
  }));
  out.events = out.events.filter((event) => event.name);
  // the analyzer can list an attribute twice -- once bare from a doc tag, once from its field -- so
  // merge them, each filling in what the other leaves out
  const attributes = new Map();
  for (const attr of out.attributes)
    attributes.set(attr.name, { ...attr, ...attributes.get(attr.name) });
  out.attributes = [...attributes.values()];
  // Vaadin's analyzer points an array or object property at the attribute Polymer would derive for
  // it, yet leaves that attribute out of `attributes`. Such a property -- a grid's `items` -- is a
  // declared input set as a property only, so it is listed as the element's own field, not as the
  // plumbing of whichever of the element's mixins declares it.
  for (const member of out.members ?? []) {
    if (!member.attribute || attributes.has(member.attribute)) continue;
    delete member.attribute;
    delete member.inheritedFrom;
  }
  // the analyzer's expanded type (`'primary' | 'outline' | ...`) where the declared one is an alias
  // (`ButtonAppearance`) that means nothing without the library's sources, and without Closure's
  // non-null marker (`!Array<!GridItem>`), which a TypeScript reading does not expect
  for (const entry of [...out.attributes, ...(out.members ?? [])]) {
    if (entry.parsedType?.text) entry.type = { text: entry.parsedType.text };
    if (entry.type?.text?.includes("!"))
      entry.type = {
        ...entry.type,
        text: entry.type.text.replace(/!(?=[\w(])/g, ""),
      };
  }
  return out;
}

const missing = new Set();
const modules = [];
let schemaVersion;
for (const name of PACKAGES) {
  const owner = manifestOf(name, ".");
  schemaVersion ??= owner.manifest.schemaVersion;
  for (const mod of owner.manifest.modules ?? []) {
    const declarations = (mod.declarations ?? [])
      .filter((decl) => decl.customElement && decl.tagName)
      .map((decl) => resolve(decl, owner, missing))
      .filter((decl) => !REGISTERED || REGISTERED.has(decl.tagName));
    if (declarations.length)
      modules.push({
        kind: mod.kind,
        path: `${name}/${mod.path}`,
        declarations,
      });
  }
}
fs.writeFileSync(
  OUT,
  `${JSON.stringify({ schemaVersion, modules }, null, 2)}\n`,
);
if (missing.size) {
  console.error(
    `no manifest declares: ${[...missing].join(", ")} -- add them to tools/unpublished.json`,
  );
  process.exitCode = 1;
}
