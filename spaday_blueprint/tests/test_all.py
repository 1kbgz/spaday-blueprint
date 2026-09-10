import ast
from pathlib import Path

from spaday import element, generate
from spaday.bootstrap import bootstrap

from spaday_blueprint import TOKENS, BpButton, BpCard, BpIcon, package

ROOT = Path(__file__).parent.parent


def test_generated_components_serialize():
    node = BpCard(BpButton(action="primary", status="accent").text("Save"), BpIcon(shape="user")).to_node()
    assert node["tag"] == "bp-card"
    assert [child["tag"] for child in node["slots"]["default"]] == ["bp-button", "bp-icon"]
    assert node["slots"]["default"][0]["props"]["action"] == {"Str": "primary"}


def test_catalog_covers_both_packages():
    tags = {schema.tag for schema in package.catalog}
    assert {"bp-button", "bp-card", "bp-input"} <= tags
    assert "bp-icon" in tags  # registered by @blueprintui/icons, not the components package
    assert len(tags) == len(package.catalog)


def test_package_drives_bootstrap_asset_urls():
    html = bootstrap(packages=[package])
    assert 'href="/components/blueprint/css/blueprint.css"' in html
    assert 'src="/components/blueprint/cdn/index.js"' in html
    assert '"@blueprintui/components/include/": "/components/blueprint/vendor/@blueprintui/components/dist/include/"' in html
    # the bundle's own imports resolve through the map, so it must come first
    assert html.index('type="importmap"') < html.index('src="/components/blueprint/cdn/index.js"')


def test_published_imports_are_served():
    assert package.imports, "the JS build writes the import map; run it first"
    for specifier, path in package.imports:
        target = package.assets_dir / path
        assert target.is_dir() if path.endswith("/") else target.is_file(), f"{specifier} maps to {path}, which the build did not produce"


def test_tokens_are_blueprint_tokens_the_css_kwarg_produces():
    for kwarg, (prop, description) in TOKENS.items():
        assert prop.startswith("--bp-") and description.startswith("drives --spa-")
        assert element("div").css(**{kwarg: "x"}).to_node()["props"]["style"]["Str"] == f"{prop}: x"


def test_generated_catalog_is_current():
    fresh = generate(str(ROOT / "custom-elements.json"))
    assert ast.dump(ast.parse(fresh)) == ast.dump(ast.parse((ROOT / "components.py").read_text(encoding="utf-8")))
