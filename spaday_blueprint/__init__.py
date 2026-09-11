import json
from pathlib import Path

from spaday import ComponentPackage

from . import components as _components
from .components import *
from .components import __all__ as _component_names

__version__ = "0.1.0"

_EXTENSION = Path(__file__).parent / "extension"
# Blueprint's modules under its own bare specifiers, written by the JS build (js/tools/vendor.mjs): a
# library on the page that imports Blueprint resolves to this copy instead of registering the same
# tags a second time
_IMPORTS = _EXTENSION / "vendor" / "imports.json"

# the exact version of each JS library the package serves, written by its JS build
_VERSIONS = _EXTENSION / "versions.json"

package = ComponentPackage(
    name="blueprint",
    assets_dir=_EXTENSION,
    assets=(("css", "css/blueprint.css"), ("js", "cdn/index.js")),
    components=tuple(getattr(_components, name) for name in _component_names),
    imports=tuple(json.loads(_IMPORTS.read_text(encoding="utf-8")).items()) if _IMPORTS.exists() else (),
    provides=json.loads(_VERSIONS.read_text(encoding="utf-8")) if _VERSIONS.exists() else {},
)

#: ``css()`` kwarg → (CSS custom property, what it controls), in the shape of
#: :data:`spaday.theme.SHELL_TOKENS`.
#:
#: Blueprint is a design system, so this package themes the *other* way round from a rendering
#: package: rather than exposing ``--spa-blueprint-*`` tokens of its own, its stylesheet maps
#: Blueprint's tokens onto the ``--spa-*`` palette that spaday's shell and every other component
#: package reads. Set these and the whole page follows — shell, graphs, tables, trees::
#:
#:     App().css(bp_status_accent_background_200="#0C4253")
#:
#: Every other Blueprint token works the same way (``css()`` takes arbitrary custom properties);
#: these are the ones wired to the shell palette.
TOKENS = {
    "bp_layer_background_200": ("--bp-layer-background-200", "drives --spa-surface"),
    "bp_layer_background_100": ("--bp-layer-background-100", "drives --spa-surface-2"),
    "bp_object_border_color_100": ("--bp-object-border-color-100", "drives --spa-border"),
    "bp_text_color_400": ("--bp-text-color-400", "drives --spa-muted"),
    "bp_status_accent_background_200": ("--bp-status-accent-background-200", "drives --spa-accent and --spa-info"),
    "bp_status_success_background_200": ("--bp-status-success-background-200", "drives --spa-success"),
    "bp_status_warning_background_200": ("--bp-status-warning-background-200", "drives --spa-warning"),
    "bp_status_danger_background_200": ("--bp-status-danger-background-200", "drives --spa-danger"),
}

__all__ = [*_component_names, "TOKENS", "package"]  # noqa: PLE0604
