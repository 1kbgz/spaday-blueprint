"""A spaday page on spaday-blueprint, shared with a downstream library through the import map.

The integration this exercises end to end:

* the generated catalog authored in Python and wired with spaday's own state -- two ``BpButton``\\ s
  drive a store field that a ``BpBadge`` reads;
* a downstream library that imports Blueprint by its bare specifiers, left as imports in its
  bundle, which the page's import map resolves to spaday-blueprint's copy, so nothing registers the
  same tags twice. It has no Python of its own beyond a schema-carrying :class:`~spaday.Component`
  and a :class:`~spaday.ComponentPackage` serving its bundle.

Served for the browser tests; ``/conformance.js`` hands back the check that the package's own
bundle implements the catalog generated for it.
"""

from pathlib import Path

import uvicorn
from spaday import Component, ComponentPackage, ComponentSchema, PropertySchema, SetField, check_script, element
from spaday.backends.starlette import serve
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from spaday_blueprint import BpBadge, BpButton, BpCard, BpIcon, package as blueprint_package


class DemoAction(Component):
    """The downstream library's element, bound from Python with no Python of its own."""

    tag = "demo-action"
    schema = ComponentSchema(
        tag="demo-action",
        class_name="DemoAction",
        summary="An action built from Blueprint's button.",
        props=(PropertySchema(name="label", kind="string", description="Button label."),),
    )


downstream_package = ComponentPackage(
    name="demo-downstream",
    assets_dir=Path(__file__).parent / "downstream",
    assets=(("js", "downstream.js"),),
    components=(DemoAction,),
)

page = element("div", id="app").child(
    BpCard(id="card").child(
        BpButton(id="approve", action="primary", status="success").text("Approve").on("click", SetField("state", "approved")),
        BpButton(id="reject", action="secondary", status="danger").text("Reject").on("click", SetField("state", "rejected")),
        BpBadge(id="badge").bind("textContent", "state"),
        BpIcon(id="icon", shape="user"),
    ),
    DemoAction(id="downstream", label="Downstream"),
)


async def conformance(request) -> PlainTextResponse:
    """The browser-side check of spaday-blueprint's own bundle against its generated catalog."""
    return PlainTextResponse(check_script([blueprint_package]), media_type="text/plain")


app = serve(
    page,
    packages=[blueprint_package, downstream_package],
    routes=[Route("/conformance.js", conformance)],
    store={"state": "pending"},
    title="spaday-blueprint integration",
)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8018)
