"""Gallery of every Blueprint component wrapped by spaday-blueprint."""

from __future__ import annotations

import io
import keyword
import textwrap
import tokenize

from spaday import Invoke, by_id, element
from spaday.backends.starlette import serve

from . import components as bp, package

COMPONENT_SNIPPETS: list[str] = []


def _snippet(names: str, body: str) -> str:
    source = f"from spaday_blueprint import {names}\n\n{textwrap.dedent(body).strip()}\n"
    COMPONENT_SNIPPETS.append(source)
    return source


def _offsets(source: str) -> list[int]:
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def _code(source: str):
    """Render a dependency-free highlighted Python code block."""
    offsets = _offsets(source)
    children = []
    cursor = 0
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.ENDMARKER:
            continue
        start = offsets[token.start[0] - 1] + token.start[1]
        end = offsets[token.end[0] - 1] + token.end[1]
        if start > cursor:
            children.append(source[cursor:start])
        token_class = None
        if token.type == tokenize.NAME and keyword.iskeyword(token.string):
            token_class = "keyword"
        elif token.type == tokenize.STRING:
            token_class = "string"
        elif token.type == tokenize.NUMBER:
            token_class = "number"
        elif token.type == tokenize.COMMENT:
            token_class = "comment"
        elif token.type == tokenize.OP:
            token_class = "operator"
        children.append(element("span", class_=f"token-{token_class}").text(token.string) if token_class else token.string)
        cursor = end
    if cursor < len(source):
        children.append(source[cursor:])
    return element("pre", element("code", *children), class_="code-block")


def _demo(title: str, description: str, source: str, preview):
    return bp.BpCard(
        element(
            "header",
            element("div", element("h3").text(title), element("p").text(description)),
            bp.BpButtonCopy(value=source, **{"aria-label": f"Copy {title} example"}),
            class_="demo-heading",
        ),
        element("div", preview, class_="preview"),
        _code(source),
        class_="gallery-card",
    )


def _section(section_id: str, title: str, description: str, *cards):
    return element(
        "section",
        element("header", element("p", class_="section-label").text(section_id.upper()), element("h2").text(title), element("p").text(description)),
        element("div", *cards, class_="gallery-grid"),
        id=section_id,
        class_="gallery-section",
    )


actions = _section(
    "actions",
    "Actions and identity",
    "Buttons, status labels, and compact identity primitives.",
    _demo(
        "Button family",
        "Primary, grouped, icon, expansion, handle, resize, sort, and copy actions.",
        _snippet(
            "BpButton, BpButtonCopy, BpButtonExpand, BpButtonGroup, BpButtonHandle, BpButtonIcon, BpButtonResize, BpButtonSort",
            """
            actions = BpButtonGroup(
                BpButton(action="primary", status="accent").text("Deploy"),
                BpButtonIcon(shape="ellipsis").text("More"),
                BpButtonCopy(value="v2.16.0"),
                BpButtonExpand(),
                BpButtonHandle(),
                BpButtonSort(),
            )
            resize = BpButtonResize()
            """,
        ),
        element(
            "div",
            bp.BpButtonGroup(
                bp.BpButton(action="primary", status="accent").text("Deploy"),
                bp.BpButtonIcon(shape="ellipsis").text("More"),
                bp.BpButtonCopy(value="v2.16.0"),
                bp.BpButtonExpand(),
                bp.BpButtonHandle(),
                bp.BpButtonSort(),
            ),
            element("div", "Resizable boundary", bp.BpButtonResize(), class_="resize-preview"),
            class_="stack",
        ),
    ),
    _demo(
        "Identity and status",
        "Combine avatars, icons, badges, and tags into compact summaries.",
        _snippet(
            "BpAvatar, BpBadge, BpIcon, BpTag",
            """
            identity = BpAvatar(
                BpIcon(shape="user", status="accent"),
                shape="circle",
                status="accent",
            )
            status = BpBadge(status="success").text("Healthy")
            label = BpTag(status="accent", readonly=True).text("production")
            """,
        ),
        element(
            "div",
            bp.BpAvatar(bp.BpIcon(shape="user", status="accent"), shape="circle", status="accent"),
            bp.BpBadge(status="success").text("Healthy"),
            bp.BpTag(status="accent", readonly=True).text("production"),
            class_="inline-preview",
        ),
    ),
)

forms = _section(
    "forms",
    "Forms",
    "Typed inputs, selections, validation messages, and form structure.",
    _demo(
        "Text inputs",
        "Collect text with labels, hints, search, password, phone, and multiline variants.",
        _snippet(
            "BpField, BpFieldMessage, BpInput, BpPassword, BpPin, BpSearch, BpTelephone, BpTextarea",
            """
            fields = BpField(
                element("label").text("Project"),
                BpInput(value="Apollo"),
                BpFieldMessage().text("Use a memorable name"),
            )
            password = BpPassword(value="secret")
            pin = BpPin(value="3141", length=4)
            search = BpSearch(placeholder="Search releases")
            phone = BpTelephone(value="+1 212 555 0100")
            notes = BpTextarea(rows=3, value="Ready for review")
            """,
        ),
        element(
            "div",
            bp.BpField(element("label").text("Project"), bp.BpInput(value="Apollo"), bp.BpFieldMessage().text("Use a memorable name")),
            bp.BpPassword(value="secret", **{"aria-label": "Password"}),
            bp.BpPin(value="3141", length=4, **{"aria-label": "PIN"}),
            bp.BpSearch(placeholder="Search releases", **{"aria-label": "Search releases"}),
            bp.BpTelephone(value="+1 212 555 0100", **{"aria-label": "Telephone"}),
            bp.BpTextarea(rows=3, value="Ready for review", **{"aria-label": "Notes"}),
            class_="form-preview",
        ),
    ),
    _demo(
        "Dates and numbers",
        "Native date, time, color, range, number, and stepper controls.",
        _snippet(
            "BpColor, BpDate, BpMonth, BpNumber, BpNumberStepper, BpRange, BpTime",
            """
            color = BpColor(value="#2563eb")
            date = BpDate(value="2026-09-11")
            month = BpMonth(value="2026-09")
            number = BpNumber(value="12", min=0, max=100)
            stepper = BpNumberStepper(value=12)
            progress = BpRange(value="65", min=0, max=100)
            time = BpTime(value="09:30")
            """,
        ),
        element(
            "div",
            bp.BpColor(value="#2563eb", **{"aria-label": "Accent color"}),
            bp.BpDate(value="2026-09-11", **{"aria-label": "Date"}),
            bp.BpMonth(value="2026-09", **{"aria-label": "Month"}),
            bp.BpNumber(value="12", min=0, max=100, **{"aria-label": "Number"}),
            bp.BpNumberStepper(value=12, min=0, max=100, **{"aria-label": "Number stepper"}),
            bp.BpRange(value="65", min=0, max=100, **{"aria-label": "Progress"}),
            bp.BpTime(value="09:30", **{"aria-label": "Time"}),
            class_="form-preview compact-controls",
        ),
    ),
    _demo(
        "Selection controls",
        "Binary, single-choice, rating, and immediate toggle controls.",
        _snippet(
            "BpCheckbox, BpRadio, BpRating, BpSwitch",
            """
            checkbox = BpCheckbox(checked=True)
            radio = BpRadio(name="plan", value="pro", checked=True)
            rating = BpRating(value=4, max=5)
            switch = BpSwitch(checked=True)
            """,
        ),
        element(
            "div",
            element("label", bp.BpCheckbox(checked=True), " Email alerts"),
            element("label", bp.BpRadio(name="plan", value="pro", checked=True), " Pro plan"),
            bp.BpRating(value=4, max=5, **{"aria-label": "Quality"}),
            element("label", bp.BpSwitch(checked=True), " Automatic updates"),
            class_="form-preview selection-preview",
        ),
    ),
    _demo(
        "Select and upload",
        "Group controls, provide options, and accept local files.",
        _snippet(
            "BpFieldset, BpFile, BpFormGroup, BpOption, BpSelect",
            """
            form = BpFormGroup(
                BpFieldset(
                    element("label").text("Region"),
                    BpSelect(
                        BpOption(value="east").text("US East"),
                        BpOption(value="west").text("US West"),
                        value="east",
                    ),
                ),
                BpFile(accept=".json"),
            )
            """,
        ),
        bp.BpFormGroup(
            bp.BpFieldset(
                element("label").text("Region"),
                bp.BpSelect(bp.BpOption(value="east").text("US East"), bp.BpOption(value="west").text("US West"), value="east"),
            ),
            bp.BpFile(accept=".json", **{"aria-label": "Configuration file"}),
            class_="form-preview",
        ),
    ),
)

content = _section(
    "content",
    "Content and disclosure",
    "Cards, progressive disclosure, chat, and loading placeholders.",
    _demo(
        "Accordion",
        "Compose headers and content into expandable panels.",
        _snippet(
            "BpAccordion, BpAccordionContent, BpAccordionHeader, BpAccordionPanel",
            """
            accordion = BpAccordion(
                BpAccordionPanel(
                    BpAccordionHeader().text("What is Spaday?"),
                    BpAccordionContent().text("Typed Python components."),
                    expanded=True,
                )
            )
            """,
        ),
        bp.BpAccordion(
            bp.BpAccordionPanel(
                bp.BpAccordionHeader().text("What is Spaday?"),
                bp.BpAccordionContent().text("Typed Python components rendered in the browser."),
                expanded=True,
            )
        ),
    ),
    _demo(
        "Card and divider",
        "Group related content into a clear visual surface.",
        _snippet(
            "BpCard, BpDivider, BpSkeleton",
            """
            card = (
                BpCard("Deployment is healthy")
                .child_in("header", "Production")
                .child_in("footer", "Updated now")
            )
            divider = BpDivider()
            loading = BpSkeleton(effect="sheen")
            """,
        ),
        bp.BpCard(
            element("p").text("Deployment is healthy"),
            bp.BpDivider(),
            bp.BpSkeleton(effect="sheen", class_="skeleton-demo"),
            class_="nested-card",
        )
        .child_in("header", element("strong").text("Production"))
        .child_in("footer", element("small").text("Updated now")),
    ),
    _demo(
        "Chat",
        "Arrange incoming and outgoing messages with progress state.",
        _snippet(
            "BpChatGroup, BpChatMessage",
            """
            chat = BpChatGroup(
                BpChatMessage(type="received").text("Ready to deploy?"),
                BpChatMessage(type="sent", color="accent").text("Ship it."),
            )
            """,
        ),
        bp.BpChatGroup(
            bp.BpChatMessage(type="received").text("Ready to deploy?"),
            bp.BpChatMessage(type="sent", color="accent").text("Ship it."),
        ),
    ),
)

navigation = _section(
    "navigation",
    "Navigation",
    "Wayfinding for menus, pages, steps, tabs, and trees.",
    _demo(
        "Breadcrumb",
        "Show location within a hierarchy.",
        _snippet(
            "BpBreadcrumb",
            'trail = BpBreadcrumb(element("a", href="#").text("Home"), element("a", href="#navigation").text("Components"), "Gallery")',
        ),
        bp.BpBreadcrumb(
            element("a", href="#").text("Home"),
            element("a", href="#navigation").text("Components"),
            element("span").text("Gallery"),
        ),
    ),
    _demo(
        "Dropdown menu",
        "Place a menu behind a compact trigger.",
        _snippet(
            "BpDropdown, BpMenu, BpMenuItem",
            """
            menu = BpDropdown(
                BpMenu(
                    BpMenuItem().text("Rename"),
                    BpMenuItem().text("Archive"),
                ),
                id="actions",
            )
            """,
        ),
        element(
            "div",
            bp.BpButton(popovertarget="gallery-actions").text("Actions"),
            bp.BpDropdown(
                bp.BpMenu(bp.BpMenuItem().text("Rename"), bp.BpMenuItem().text("Archive")),
                id="gallery-actions",
                position="bottom-start",
            ),
        ),
    ),
    _demo(
        "Navigation tree",
        "Group application destinations into expandable navigation.",
        _snippet(
            "BpNav, BpNavGroup, BpNavItem",
            """
            nav = BpNav(
                BpNavGroup(
                    BpNavItem(selected=True).text("Overview"),
                    BpNavItem().text("Activity"),
                    expanded=True,
                )
            )
            """,
        ),
        bp.BpNav(
            bp.BpNavGroup(
                bp.BpNavItem(selected=True).text("Overview"),
                bp.BpNavItem().text("Activity"),
                expanded=True,
            ),
            class_="mini-nav",
        ),
    ),
    _demo(
        "Pagination",
        "Move through pages directly or with an input.",
        _snippet(
            "BpPagination, BpPaginationInput",
            """
            pages = BpPagination(
                BpPaginationInput(value=3, total=12),
                aria_label="Results",
            )
            """,
        ),
        bp.BpPagination(bp.BpPaginationInput(value=3, total=12), **{"aria-label": "Results"}),
    ),
    _demo(
        "Stepper",
        "Communicate progress through a multistep process.",
        _snippet(
            "BpStepper, BpStepperItem",
            """
            steps = BpStepper(
                BpStepperItem(status="success").text("Build"),
                BpStepperItem(selected=True).text("Review"),
                BpStepperItem().text("Deploy"),
            )
            """,
        ),
        bp.BpStepper(
            bp.BpStepperItem(status="success").text("Build"),
            bp.BpStepperItem(selected=True).text("Review"),
            bp.BpStepperItem().text("Deploy"),
        ),
    ),
    _demo(
        "Tabs",
        "Switch among related panels.",
        _snippet(
            "BpTab, BpTabList, BpTabPanel, BpTabs",
            """
            tabs = BpTabs(
                BpTabList(
                    BpTab(selected=True).text("Overview"),
                    BpTab().text("Activity"),
                ),
                BpTabPanel("Overview content"),
                BpTabPanel("Activity content"),
            )
            """,
        ),
        bp.BpTabs(
            bp.BpTabList(bp.BpTab(selected=True).text("Overview"), bp.BpTab().text("Activity")),
            bp.BpTabPanel("Overview content"),
            bp.BpTabPanel("Activity content"),
        ),
    ),
    _demo(
        "Tree",
        "Navigate nested, selectable items.",
        _snippet(
            "BpTree, BpTreeItem",
            """
            tree = BpTree(
                BpTreeItem(
                    "spaday_blueprint",
                    BpTreeItem().text("gallery.py"),
                    BpTreeItem().text("example.py"),
                    expanded=True,
                ),
                selectable="single",
            )
            """,
        ),
        bp.BpTree(
            bp.BpTreeItem(
                "spaday_blueprint",
                bp.BpTreeItem().text("gallery.py"),
                bp.BpTreeItem().text("example.py"),
                expanded=True,
            ),
            selectable="single",
        ),
    ),
)

layout = _section(
    "layout",
    "Application layout",
    "Headers, panels, and responsive page regions for application shells.",
    _demo(
        "Page shell",
        "Compose a header, navigation panel, main content, and footer.",
        _snippet(
            "BpHeader, BpHeaderItem, BpPage, BpPanel",
            """
            shell = (
                BpPage("Main content")
                .child_in("header", BpHeader(BpHeaderItem().text("Blueprint")))
                .child_in("aside-start", BpPanel("Navigation"))
                .child_in("footer", "Status: ready")
            )
            """,
        ),
        bp.BpPage("Main content", class_="mini-page")
        .child_in("header", bp.BpHeader(bp.BpHeaderItem().text("Blueprint")))
        .child_in("aside-start", bp.BpPanel("Navigation"))
        .child_in("footer", "Status: ready"),
    ),
)

feedback = _section(
    "feedback",
    "Feedback and overlays",
    "Alerts, progress, transient messages, and focused overlay content.",
    _demo(
        "Alerts",
        "Stack related status messages by severity.",
        _snippet(
            "BpAlert, BpAlertGroup",
            """
            alerts = BpAlertGroup(
                BpAlert(status="success").text("Deployment complete"),
                BpAlert(status="warning").text("One check is pending"),
                status="accent",
            )
            """,
        ),
        bp.BpAlertGroup(
            bp.BpAlert(status="success").text("Deployment complete"),
            bp.BpAlert(status="warning").text("One check is pending"),
            status="accent",
        ),
    ),
    _demo(
        "Progress",
        "Show determinate, circular, and indeterminate progress.",
        _snippet(
            "BpProgressBar, BpProgressCircle, BpProgressDot",
            """
            bar = BpProgressBar(value=65, max=100, status="accent")
            circle = BpProgressCircle(value=65, status="success")
            dots = BpProgressDot(size="md")
            """,
        ),
        element(
            "div",
            bp.BpProgressBar(value=65, max=100, status="accent"),
            element("div", bp.BpProgressCircle(value=65, status="success"), bp.BpProgressDot(size="md"), class_="inline-preview"),
            class_="stack",
        ),
    ),
    _demo(
        "Dialog and drawer",
        "Open focused tasks and secondary content on demand.",
        _snippet(
            "BpDialog, BpDrawer",
            """
            dialog = BpDialog("Saved", id="saved", modal=True)
            drawer = BpDrawer("Filters", id="filters", position="inline-end")
            """,
        ),
        element(
            "div",
            bp.BpButton().text("Open dialog").on("click", Invoke(by_id("gallery-dialog"), "showPopover")),
            bp.BpButton().text("Open drawer").on("click", Invoke(by_id("gallery-drawer"), "showPopover")),
            bp.BpDialog("Changes have been saved.", id="gallery-dialog", modal=True, closable=True).child_in("header", "Saved"),
            bp.BpDrawer("Filters go here.", id="gallery-drawer", position="inline-end", closable=True),
            class_="inline-preview",
        ),
    ),
    _demo(
        "Toast and tips",
        "Provide transient feedback and contextual guidance.",
        _snippet(
            "BpButtonIcon, BpToast, BpToggletip, BpTooltip",
            """
            toast = BpToast("Settings saved", id="saved-toast", status="success")
            details = BpButtonIcon(
                id="details-button",
                shape="info",
                popovertarget="details-tip",
            )
            toggletip = BpToggletip(
                "More details",
                id="details-tip",
                anchor="details-button",
            )
            help_button = BpButtonIcon(shape="help", interestfor="refresh-tip")
            tooltip = BpTooltip("Refresh data", id="refresh-tip")
            """,
        ),
        element(
            "div",
            bp.BpButton().text("Show toast").on("click", Invoke(by_id("gallery-toast"), "showPopover")),
            bp.BpToast("Settings saved", id="gallery-toast", status="success", closable=True),
            bp.BpButtonIcon(
                id="gallery-details-button",
                shape="info",
                popovertarget="gallery-toggletip",
                **{"aria-label": "More details"},
            ),
            bp.BpToggletip("More details", id="gallery-toggletip", anchor="gallery-details-button", closable=True),
            bp.BpButtonIcon(shape="help", interestfor="gallery-tooltip", **{"aria-label": "Refresh help"}),
            bp.BpTooltip("Refresh data", id="gallery-tooltip"),
            class_="inline-preview",
        ),
    ),
)

formatting = _section(
    "formatting",
    "Formatting",
    "Locale-aware values and design-token output in the browser.",
    _demo(
        "Format values",
        "Format bytes, dates, numbers, relative time, and token values.",
        _snippet(
            "BpFormatBytes, BpFormatDatetime, BpFormatNumber, BpFormatRelativeTime, BpFormatToken",
            """
            size = BpFormatBytes(value=1536000)
            date = BpFormatDatetime("2026-09-11T12:00:00Z", date_style="medium")
            price = BpFormatNumber(value=1299.5, format="currency", currency="USD")
            updated = BpFormatRelativeTime("2026-09-11T12:00:00Z", numeric="auto")
            token = BpFormatToken("--bp-status-accent-background-200")
            """,
        ),
        element(
            "dl",
            element("div", element("dt").text("Size"), element("dd", bp.BpFormatBytes(value=1536000))),
            element("div", element("dt").text("Date"), element("dd", bp.BpFormatDatetime("2026-09-11T12:00:00Z", date_style="medium"))),
            element("div", element("dt").text("Price"), element("dd", bp.BpFormatNumber(value=1299.5, format="currency", currency="USD"))),
            element("div", element("dt").text("Updated"), element("dd", bp.BpFormatRelativeTime("2026-09-11T12:00:00Z", numeric="auto"))),
            element(
                "div",
                element("dt").text("Token"),
                element("dd", bp.BpFormatToken("--bp-status-accent-background-200")),
            ),
            class_="format-list",
        ),
    ),
)

page = element(
    "main",
    element(
        "header",
        element("p", class_="eyebrow").text("SPADAY · BLUEPRINT UI"),
        element("h1").text("Component gallery"),
        element("p", class_="lede").text("Every Blueprint component currently wrapped by spaday-blueprint, with runnable Python."),
        element(
            "nav",
            *(
                element("a", href=f"#{name}").text(label)
                for name, label in [
                    ("actions", "Actions"),
                    ("forms", "Forms"),
                    ("content", "Content"),
                    ("navigation", "Navigation"),
                    ("layout", "Layout"),
                    ("feedback", "Feedback"),
                    ("formatting", "Formatting"),
                ]
            ),
            aria_label="Gallery sections",
            class_="section-nav",
        ),
        class_="hero",
    ),
    actions,
    forms,
    content,
    navigation,
    layout,
    feedback,
    formatting,
    element("footer").text(f"Generated components: {len(bp.__all__)} Blueprint elements · Python runs locally in Pyodide"),
    class_="gallery-page",
)

styles = """
<style>
  :root { color-scheme: light; }
  html { scroll-behavior: smooth; }
  body { margin: 0; background: radial-gradient(circle at 12% 0, #dbeafe 0, transparent 28rem), #f8fafc;
    color: #172033; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
  .gallery-page { box-sizing: border-box; width: min(100%, 92rem); margin: 0 auto; padding: 2.5rem 1.25rem 4rem; }
  .hero { padding: 2rem 0 1rem; }
  .eyebrow, .section-label { margin: 0; color: #2563eb; font-size: .72rem; font-weight: 800; letter-spacing: .16em; }
  h1 { margin: .35rem 0 0; font-size: clamp(2.4rem, 6vw, 4.75rem); letter-spacing: -.055em; line-height: .98; }
  .lede { max-width: 48rem; margin: 1rem 0 1.5rem; color: #64748b; font-size: 1.08rem; line-height: 1.6; }
  .section-nav { display: flex; flex-wrap: wrap; gap: .5rem; }
  .section-nav a { padding: .45rem .75rem; border: 1px solid #cbd5e1; border-radius: 999px; color: #334155;
    text-decoration: none; background: rgba(255,255,255,.9); }
  .section-nav a:hover { border-color: #2563eb; color: #1d4ed8; }
  .gallery-section { scroll-margin-top: 4rem; padding: 3rem 0 1rem; }
  .gallery-section > header { max-width: 44rem; margin-bottom: 1.25rem; }
  .gallery-section h2 { margin: .3rem 0 .4rem; font-size: 2rem; letter-spacing: -.03em; }
  .gallery-section > header > p:last-child { margin: 0; color: #64748b; }
  .gallery-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 27rem), 1fr)); gap: 1rem; align-items: start; }
  .gallery-card { display: block; min-width: 0; padding: 1.15rem; border: 1px solid #dbe3ee; border-radius: 1rem; background: white;
    box-shadow: 0 12px 35px rgba(15,23,42,.055); }
  .demo-heading { display: flex; align-items: start; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }
  .demo-heading h3 { margin: 0; font-size: 1.05rem; }
  .demo-heading p { margin: .3rem 0 0; color: #64748b; font-size: .88rem; line-height: 1.45; }
  .preview { box-sizing: border-box; min-height: 8.5rem; margin-bottom: 1rem; padding: 1.25rem; border: 1px solid #e2e8f0;
    border-radius: .75rem; background: #f8fafc; overflow: auto; }
  .preview > * { max-width: 100%; }
  .code-block { box-sizing: border-box; max-height: 18rem; margin: 0; padding: 1rem; overflow: auto; border-radius: .75rem;
    color: #dbeafe; background: #172033; font: .78rem/1.6 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    tab-size: 4; white-space: pre; }
  .token-keyword { color: #c4b5fd; } .token-string { color: #86efac; } .token-number { color: #fcd34d; }
  .token-comment { color: #94a3b8; font-style: italic; } .token-operator { color: #7dd3fc; }
  .inline-preview { display: flex; flex-wrap: wrap; align-items: center; gap: .75rem; }
  .stack, .form-preview { display: grid; gap: .8rem; }
  .resize-preview { display: flex; align-items: center; height: 2.5rem; padding-left: .75rem; border: 1px solid #cbd5e1; background: white; }
  .resize-preview bp-button-resize { margin-left: auto; }
  .compact-controls { grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: end; }
  .selection-preview label { display: inline-flex; align-items: center; gap: .45rem; }
  .nested-card { display: block; padding: 1rem; border: 1px solid #dbe3ee; border-radius: .65rem; background: white; }
  .skeleton-demo { display: block; min-height: 2.25rem; }
  .mini-nav { display: block; max-width: 16rem; }
  .mini-page { display: block; position: relative; contain: layout; min-width: 26rem; min-height: 12rem; border: 1px solid #cbd5e1;
    border-radius: .5rem; overflow: hidden; background: white; }
  .mini-page::part(internal) { position: absolute; inset: 0; min-height: 0; max-height: none; }
  .format-list { display: grid; gap: .55rem; margin: 0; }
  .format-list div { display: grid; grid-template-columns: 5rem 1fr; gap: 1rem; }
  .format-list dt { color: #64748b; } .format-list dd { margin: 0; font-weight: 700; }
  footer { margin-top: 4rem; padding-top: 1.5rem; border-top: 1px solid #cbd5e1; color: #64748b; font-size: .85rem; }
  @media (max-width: 600px) { .gallery-page { padding-inline: .75rem; } .gallery-section { padding-top: 2rem; }
    .preview { padding: .9rem; } .compact-controls { grid-template-columns: 1fr; } }
</style>
"""

app = serve(page, packages=[package], head=styles, title="spaday-blueprint gallery")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8024)
