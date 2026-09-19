import json

from spaday import Alert, Button, Checkbox, DateInput, Dialog, NumberInput, Progress, Select, Slider, TextArea, TextInput
from spaday.ui import conformance, resolve
from spaday.ui.design import _plain

from spaday_blueprint import DESIGN, package


def _props(node: dict) -> dict:
    return {key: _plain(value) for key, value in node.get("props", {}).items()}


def _find(node: dict, tag: str) -> dict:
    if node["tag"] == tag:
        return node
    for children in node.get("slots", {}).values():
        for child in children:
            if isinstance(child, dict):
                try:
                    return _find(child, tag)
                except LookupError:
                    pass
    raise LookupError(tag)


def test_the_package_publishes_its_design():
    assert package.design is DESIGN
    assert set(DESIGN.controls) == {
        "alert",
        "button",
        "checkbox",
        "date-input",
        "dialog",
        "input",
        "number-input",
        "progress",
        "select",
        "slider",
        "switch",
        "textarea",
    }


def test_fields_use_blueprint_field_composition():
    text = resolve(
        TextInput(label="Name", help="Hint", error="Bad", type="search", size="lg").bind("value", "name", mode="two-way").to_node(),
        DESIGN,
    )
    assert text["tag"] == "bp-field"
    label, help_text, control, error = text["slots"]["default"]
    assert (label["tag"], _props(label)) == ("label", {"textContent": "Name"})
    assert (control["tag"], _props(control)) == ("bp-input", {"aria-invalid": "true", "type": "search", "size": "lg"})
    assert control["bindings"] == {"value": {"field": "name", "mode": "two-way"}}
    assert (help_text["tag"], _props(help_text)) == ("bp-field-message", {"textContent": "Hint"})
    assert (error["tag"], _props(error)) == ("bp-field-message", {"class": "ui-error", "textContent": "Bad"})

    bound = _find(resolve(TextInput().bind("error", "message").to_node(), DESIGN), "bp-input")
    assert bound["bindings"]["aria-invalid"]["compute"] == {
        "expr": "cond",
        "test": {"expr": "field", "name": "message"},
        "then": {"expr": "lit", "value": "true"},
        "else": {"expr": "lit", "value": None},
    }

    textarea = _find(resolve(TextArea(rows=3, minlength=2, maxlength=20).to_node(), DESIGN), "bp-textarea")
    assert _props(textarea) == {"rows": 3, "minlength": 2, "maxlength": 20}
    number = _find(resolve(NumberInput(min=1, max=10, step=1).bind("value", "count").to_node(), DESIGN), "bp-number")
    assert number["bindings"]["value"]["codec"] == "number"
    assert _find(resolve(DateInput(min="2026-01-01").to_node(), DESIGN), "bp-date")["tag"] == "bp-date"


def test_choices_toggles_and_slider_use_blueprint_controls():
    checkbox = _find(resolve(Checkbox(label="Agree").bind("value", "agree", mode="two-way").to_node(), DESIGN), "bp-checkbox")
    assert checkbox["bindings"]["checked"] == {"field": "agree", "mode": "two-way"}
    assert checkbox["bindings"]["aria-invalid"]["compute"]["test"] == {"expr": "field", "name": "$errors.agree"}

    select = _find(resolve(Select(options=["a", {"value": 2, "label": "Two"}], value=2).to_node(), DESIGN), "bp-select")
    assert [(option["tag"], _props(option)) for option in select["slots"]["default"]] == [
        ("bp-option", {"value": '"a"', "textContent": "a"}),
        ("bp-option", {"value": "2", "selected": True, "textContent": "Two"}),
    ]
    slider = _find(resolve(Slider(min=0, max=10, step=1).bind("value", "level").to_node(), DESIGN), "bp-range")
    assert slider["bindings"]["value"]["codec"] == "number"


def test_feedback_actions_and_dialog_use_blueprint_controls():
    button = resolve(Button(label="Save", intent="primary", appearance="outline", size="lg").to_node(), DESIGN)
    assert button["tag"] == "bp-button" and _props(button) == {
        "textContent": "Save",
        "status": "accent",
        "action": "secondary",
        "size": "lg",
    }
    alert = resolve(Alert("Body", label="Portable", intent="danger").to_node(), DESIGN)
    assert alert["tag"] == "bp-alert" and _props(alert) == {"status": "danger"}
    assert _props(alert["slots"]["default"][0]) == {"textContent": "Portable"}
    progress = resolve(Progress(label="Upload", value=25, max=50).to_node(), DESIGN)
    assert progress["tag"] == "bp-progress-bar" and _props(progress) == {"label": "Upload", "value": 25, "max": 50}
    dialog = resolve(Dialog(label="Confirm").bind("open", "open", mode="two-way").to_node(), DESIGN)
    assert dialog["tag"] == "bp-dialog" and _props(dialog) == {"closable": True, "modal": True}
    assert dialog["bindings"] == {
        "open": {
            "field": "open",
            "mode": "two-way",
            "event": "close",
            "methods": ["showPopover", "hidePopover"],
            "state": "open",
        }
    }


def test_conformance_uses_one_explicit_native_fallback():
    node = resolve(conformance.page().to_node(), DESIGN)
    rendered = json.dumps(node)
    assert '"tag": "ui-' not in rendered
    assert rendered.count("data-ui-fallback") == 1
