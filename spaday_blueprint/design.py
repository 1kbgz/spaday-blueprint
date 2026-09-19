"""How Blueprint renders spaday's generic controls (:mod:`spaday.ui`)."""

from spaday.ui import ControlSpec, Design, Open, Options, Part, Value, Wrap

_SIZES = {"sm": "sm", "md": "md", "lg": "lg"}
_INTENTS = {
    "neutral": "accent",
    "primary": "accent",
    "info": "accent",
    "success": "success",
    "warning": "warning",
    "danger": "danger",
}
_FIELD = {"disabled": "disabled", "required": "required", "name": "name", "size": "size"}
_TEXT = {**_FIELD, "readonly": "readonly", "placeholder": "placeholder"}
_WRAP = Wrap(tag="bp-field")
_LABEL = Part(kind="sibling", tag="label")
_HELP = Part(kind="sibling", tag="bp-field-message")
_ERROR = Part(kind="sibling", tag="bp-field-message", props={"class": "ui-error"}, after=True)
_INVALID = {"aria-invalid": "true"}

DESIGN = Design(
    name="blueprint",
    controls={
        "button": ControlSpec(
            tag="bp-button",
            label=Part(kind="text"),
            props={"intent": "status", "appearance": "action", "size": "size", "disabled": "disabled", "name": "name"},
            values={
                "intent": _INTENTS,
                "appearance": {"filled": "primary", "outline": "secondary", "plain": "flat"},
                "size": _SIZES,
            },
        ),
        "input": ControlSpec(
            tag="bp-input",
            wrap=_WRAP,
            label=_LABEL,
            help=_HELP,
            error=_ERROR,
            invalid=_INVALID,
            props={**_TEXT, "type": "type"},
            values={"size": _SIZES},
        ),
        "textarea": ControlSpec(
            tag="bp-textarea",
            wrap=_WRAP,
            label=_LABEL,
            help=_HELP,
            error=_ERROR,
            invalid=_INVALID,
            props={**_TEXT, "rows": "rows", "minlength": "minlength", "maxlength": "maxlength"},
            values={"size": _SIZES},
        ),
        "number-input": ControlSpec(
            tag="bp-number",
            wrap=_WRAP,
            label=_LABEL,
            help=_HELP,
            error=_ERROR,
            invalid=_INVALID,
            props={**_TEXT, "min": "min", "max": "max", "step": "step"},
            values={"size": _SIZES},
            value=Value(codec="number"),
        ),
        "date-input": ControlSpec(
            tag="bp-date",
            wrap=_WRAP,
            label=_LABEL,
            help=_HELP,
            error=_ERROR,
            invalid=_INVALID,
            props={**_TEXT, "min": "min", "max": "max"},
            values={"size": _SIZES},
        ),
        "checkbox": ControlSpec(
            tag="bp-checkbox",
            wrap=_WRAP,
            label=_LABEL,
            help=_HELP,
            error=_ERROR,
            invalid=_INVALID,
            props=_FIELD,
            values={"size": _SIZES},
            value=Value(prop="checked"),
        ),
        "switch": ControlSpec(
            tag="bp-switch",
            wrap=_WRAP,
            label=_LABEL,
            help=_HELP,
            error=_ERROR,
            invalid=_INVALID,
            props=_FIELD,
            values={"size": _SIZES},
            value=Value(prop="checked"),
        ),
        "select": ControlSpec(
            tag="bp-select",
            wrap=_WRAP,
            label=_LABEL,
            help=_HELP,
            error=_ERROR,
            invalid=_INVALID,
            props={**_FIELD, "placeholder": "placeholder"},
            values={"size": _SIZES},
            options=Options(kind="children", tag="bp-option", value="value", label="text", selected="selected"),
            value=Value(codec="json"),
        ),
        "slider": ControlSpec(
            tag="bp-range",
            wrap=_WRAP,
            label=_LABEL,
            help=_HELP,
            error=_ERROR,
            invalid=_INVALID,
            props={**_FIELD, "readonly": "readonly", "min": "min", "max": "max", "step": "step"},
            values={"size": _SIZES},
            value=Value(codec="number"),
        ),
        "alert": ControlSpec(
            tag="bp-alert",
            label=Part(kind="child", tag="strong"),
            props={"intent": "status"},
            values={"intent": _INTENTS},
        ),
        "progress": ControlSpec(tag="bp-progress-bar", props={"max": "max"}),
        "dialog": ControlSpec(
            tag="bp-dialog",
            fixed={"closable": True, "modal": True},
            label=Part(kind="slot", name="header", tag="h2"),
            open=Open(prop="open", event="close", methods=("showPopover", "hidePopover"), state="open"),
        ),
    },
)

__all__ = ["DESIGN"]
