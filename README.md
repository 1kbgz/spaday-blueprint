# spaday-blueprint

Typed [Blueprint](https://blueprintui.dev) components and browser assets for [spaday](https://github.com/1kbgz/spaday).

[![Build Status](https://github.com/1kbgz/spaday-blueprint/actions/workflows/build.yaml/badge.svg?branch=main&event=push)](https://github.com/1kbgz/spaday-blueprint/actions/workflows/build.yaml)
[![codecov](https://codecov.io/gh/1kbgz/spaday-blueprint/branch/main/graph/badge.svg)](https://codecov.io/gh/1kbgz/spaday-blueprint)
[![License](https://img.shields.io/github/license/1kbgz/spaday-blueprint)](https://github.com/1kbgz/spaday-blueprint)
[![PyPI](https://img.shields.io/pypi/v/spaday-blueprint.svg)](https://pypi.python.org/pypi/spaday-blueprint)

[![Preview of Blueprint components in spaday rendering a release console](https://raw.githubusercontent.com/1kbgz/spaday-blueprint/main/docs/img/preview.webp)](https://1kbgz.github.io/spaday-blueprint/lite/)

## Overview

```python
from spaday import SetField, serve
from spaday_blueprint import BpBadge, BpButton, BpCard

page = BpCard(
    BpButton(action="primary", status="success").text("Approve").on("click", SetField("state", "approved")),
    BpBadge().bind("textContent", "state"),
)
serve(page, packages=["blueprint"], store={"state": "pending"})
```

Every Blueprint element has a typed class — 80 from `@blueprintui/components` and `BpIcon` from
`@blueprintui/icons` — generated from their Custom Elements Manifests, so props, events and slots
are checked when you author the tree. Installing the package does not inject assets; select it with
`packages=["blueprint"]` or pass the exported `package` descriptor.

## Browser examples

- [Open the standard app](https://1kbgz.github.io/spaday-blueprint/lite/) ([source](spaday_blueprint/example.py)).
- [Open the complete component gallery](https://1kbgz.github.io/spaday-blueprint/lite/?example=gallery) ([source](spaday_blueprint/gallery.py)).

Both run Python locally through Pyodide; no install or server is required.

## Run examples locally

```bash
python -m pip install -e ".[examples]"
python -m spaday_blueprint.example
python -m spaday_blueprint.gallery
```

Open `http://127.0.0.1:8023` for the standard release-console app or `http://127.0.0.1:8024` for the
component gallery. The standard app includes service metrics streamed from Python, endpoint-backed
restart and deploy actions, rollout progress, incident handling, bound forms, tabs, overlays, and shared
dark-theme state. The gallery documents every generated Blueprint component and provides a highlighted
Python snippet for each component family, including a working number stepper
instead of rendering that element.

Both pass the local package descriptor directly, so they do not install or resolve the integration from
GitHub.

## Theming

The stylesheet maps spaday's `--spa-*` shell palette onto Blueprint's own tokens, so restyling
Blueprint restyles the shell and every other spaday component package with it. `TOKENS` lists the
Blueprint tokens wired to the palette, each settable through `css()`:

```python
App().css(bp_status_accent_background_200="#0C4253")
```

Blueprint's dark theme follows spaday's page mode: a `wa-dark` class on the root (for example
`App(...).bind_root_class("wa-dark", "dark")`) or on any island switches it, and `wa-light` flips a
nested island back. Blueprint's own `bp-theme="dark"` attribute works as well.

## Sharing Blueprint with your own library

Blueprint registers global custom element names, so a second copy on the page throws from
`customElements.define`. The package serves Blueprint's modules under their own bare specifiers —
`@blueprintui/components/button`, `@blueprintui/components/include/button.js`,
`@blueprintui/icons/shapes/user.js` and the rest of their exports — through the page's import map.
A library built on Blueprint that leaves those imports out of its bundle
(`external: ["@blueprintui/components", "@blueprintui/icons"]` with esbuild) gets this copy, and
nothing registers twice.

## Known issues

- Blueprint 2.20's `bp-number-stepper` sets its `step` attribute from its constructor. The served
  module defers that default until connection so standards-compliant `document.createElement` works.
- `@blueprintui/icons`' root module omits the `BpIcon` export its types declare; the served copy
  restores it, since Blueprint's own components import it from there.

> [!NOTE]
> This library was generated using [copier](https://copier.readthedocs.io/en/stable/) from the [Base Python Project Template repository](https://github.com/python-project-templates/base).
