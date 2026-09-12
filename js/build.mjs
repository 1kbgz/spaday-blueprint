import { bundle } from "./tools/bundle.mjs";
import { bundle_css } from "./tools/css.mjs";
import { node_modules_external } from "./tools/externals.mjs";
import { vendor } from "./tools/vendor.mjs";

import fs from "fs";
import path from "path";
import cpy from "cpy";

// The libraries served under their own bare specifiers (see tools/vendor.mjs): the components and
// the icons package, which registers <bp-icon>.
const VENDORED = ["@blueprintui/components", "@blueprintui/icons"];

// @blueprintui/icons' root module drops the re-export its own types declare (`export * from
// './icon/index.js'`), so `import { BpIcon } from "@blueprintui/icons"` -- which Blueprint's own
// include/time.js does -- finds nothing, and in a browser with scoped element registries
// defineScopedElement then throws on the undefined class and takes the whole catalog down. Serve
// the module its types describe.
const numberStepperPath =
  "node_modules/@blueprintui/components/dist/number-stepper/element.js";
const numberStepperSource = fs.readFileSync(numberStepperPath, "utf8");
const constructorDefault = "this.value = 0, this.step = 1";
const connectedDefault = "connectedCallback() {\n\t\tsuper.connectedCallback()";
if (
  !numberStepperSource.includes(constructorDefault) ||
  !numberStepperSource.includes(connectedDefault)
) {
  throw new Error("Blueprint number-stepper implementation changed");
}

const PATCHES = {
  "@blueprintui/icons/dist/index.js": 'export * from "./icon/index.js";\n',
  "@blueprintui/components/dist/number-stepper/element.js": numberStepperSource
    .replace(constructorDefault, "this.value = 0")
    .replace(
      connectedDefault,
      "connectedCallback() {\n\t\tthis.step ??= 1, super.connectedCallback()",
    ),
};

// Every include module, each registering its elements: include/all.js leaves some out (the
// formatters, stepper, toast, toggletip, ...)
const INCLUDE = "node_modules/@blueprintui/components/dist/include";
const includes = fs
  .readdirSync(INCLUDE)
  .filter((file) => file.endsWith(".js") && file !== "all.js")
  .map((file) => `import "@blueprintui/components/include/${file}";`)
  .join("\n");

const VERSION = JSON.parse(
  fs.readFileSync("node_modules/@blueprintui/components/package.json", "utf8"),
).version;

// the elements this bundle serves: the define-guard warns about any that another copy registered first
const TAGS = JSON.parse(
  fs.readFileSync("../spaday_blueprint/custom-elements.json", "utf8"),
)
  .modules.flatMap((mod) => mod.declarations.map((decl) => decl.tagName))
  .filter(Boolean);
const define = { __BLUEPRINT_VERSION__: JSON.stringify(VERSION) };
// the version actually served, so a page holding a second copy can compare and refuse rather than
// half-work
const publishVersion = `Object.defineProperty(globalThis, "__spadayBlueprint", { value: Object.freeze({ version: ${JSON.stringify(VERSION)} }), configurable: true });\n`;

// The bundle registers the catalog through the vendored modules, so Blueprint's specifiers stay
// imports, resolved by the page's import map. The define-guard is a module of its own, imported
// first: every import evaluates before the importing module's body, so an inlined guard would
// install too late.
const keepImports = {
  name: "keep-imports",
  setup(build) {
    build.onResolve(
      { filter: /^(@blueprintui\/|\.\/define-guard\.js$)/ },
      (args) => ({ path: args.path, external: true }),
    );
  },
};

const BUNDLES = [
  {
    entryPoints: ["src/ts/index.ts"],
    plugins: [node_modules_external()],
    outfile: "dist/esm/index.js",
    define,
  },
  {
    entryPoints: ["src/ts/define-guard.ts"],
    outfile: "dist/cdn/define-guard.js",
  },
  {
    stdin: {
      contents: `import { restoreDefine } from "./define-guard.js";\n${includes}\nrestoreDefine(${JSON.stringify(`@blueprintui/components ${VERSION}`)}, ${JSON.stringify(TAGS)});\n${publishVersion}`,
      resolveDir: ".",
      loader: "js",
    },
    plugins: [keepImports],
    outfile: "dist/cdn/index.js",
  },
];

// Blueprint switches theme with a bp-theme attribute; spaday's page mode is a wa-dark / wa-light
// class, on the root or on an island. Attach each theme to the matching class too, so a page on
// spaday's convention re-themes Blueprint with it. Fails loudly if an upgrade renames the selector.
const PAGE_MODE = {
  "themes/dist/index.css": [
    ':root, [bp-theme~=""] {',
    ':root, [bp-theme~=""], .wa-light {',
  ],
  "themes/dist/dark/index.css": [
    '[bp-theme~="dark"] {',
    '[bp-theme~="dark"], .wa-dark {',
  ],
};
const pageMode = {
  resolve: (specifier, from) => path.resolve(path.dirname(from), specifier),
  read(file) {
    const text = fs.readFileSync(file, "utf8");
    const rule = Object.entries(PAGE_MODE).find(([suffix]) =>
      file.endsWith(suffix),
    );
    if (!rule) return text;
    const [from, to] = rule[1];
    if (!text.includes(from))
      throw new Error(`${file} no longer declares ${from}`);
    return text.replace(from, to);
  },
};

async function build() {
  fs.rmSync("dist", { recursive: true, force: true });
  fs.rmSync("../spaday_blueprint/extension", {
    recursive: true,
    force: true,
  });

  await bundle_css("src/css/blueprint.css", pageMode);

  await Promise.all(BUNDLES.map(bundle)).catch(() => process.exit(1));

  // the import map, relative to the served root: read by the Python package, and inlined into the
  // test page with URLs relative to it
  const imports = Object.fromEntries(
    Object.entries(await vendor(VENDORED, "dist/vendor", PATCHES)).map(
      ([specifier, file]) => [specifier, `vendor/${file}`],
    ),
  );
  fs.writeFileSync(
    "dist/vendor/imports.json",
    `${JSON.stringify(imports, null, 2)}\n`,
  );
  const map = JSON.stringify(
    {
      imports: Object.fromEntries(
        Object.entries(imports).map(([k, v]) => [k, `./${v}`]),
      ),
    },
    null,
    2,
  );
  const html = fs
    .readFileSync("src/html/index.html", "utf8")
    .replace(
      "<!-- importmap -->",
      `<script type="importmap">\n${map}\n    </script>`,
    );
  fs.writeFileSync("dist/index.html", html);

  // the exact version of every library this package serves, read by the Python package as its
  // ComponentPackage.provides, so spaday can reconcile it with the other packages on a page
  const { dependencies = {} } = JSON.parse(
    fs.readFileSync("package.json", "utf8"),
  );
  const served = Object.fromEntries(
    Object.keys(dependencies).map((name) => [
      name,
      JSON.parse(fs.readFileSync(`node_modules/${name}/package.json`, "utf8"))
        .version,
    ]),
  );
  fs.writeFileSync(
    "dist/versions.json",
    `${JSON.stringify(served, null, 2)}\n`,
  );

  // Copy servable assets to python extension (exclude esm/)
  fs.mkdirSync("../spaday_blueprint/extension", { recursive: true });
  await cpy("dist/**/*", "../spaday_blueprint/extension", {
    filter: (file) =>
      !file.relativePath.startsWith("esm/") &&
      !file.relativePath.startsWith("dist/esm/"),
  });
}

await build();
