import asyncio
import logging
from datetime import UTC, date, datetime, timedelta

import transports
import uvicorn
from pydantic import BaseModel
from spaday import CallEndpoint, Invoke, Sequence, SetField, by_id, concat, cond, element, eq, field, item, obj
from spaday.backends.starlette import serve
from spaday.components.shell import App, Body, Each, Main, Nav, Row
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute

from spaday_blueprint import (
    BpAlert,
    BpBadge,
    BpButton,
    BpCard,
    BpCheckbox,
    BpDate,
    BpDialog,
    BpField,
    BpFieldMessage,
    BpFieldset,
    BpFormatBytes,
    BpFormatNumber,
    BpFormatRelativeTime,
    BpIcon,
    BpInput,
    BpNumber,
    BpOption,
    BpProgressBar,
    BpProgressCircle,
    BpRadio,
    BpRange,
    BpSelect,
    BpSwitch,
    BpTab,
    BpTabList,
    BpTabPanel,
    BpTabs,
    BpTag,
    BpTextarea,
    BpToast,
    package,
)

logger = logging.getLogger("uvicorn.error")

TODAY = date(2026, 9, 14)
# key: (name, version, cpu %, memory bytes, requests/s)
SERVICES = {
    "api": ("Public API", "v2.14.0", 42, 1.9e9, 1840),
    "worker": ("Job workers", "v1.8.3", 67, 3.2e9, 420),
    "search": ("Search", "v5.2.1", 31, 5.6e9, 960),
    "billing": ("Billing", "v3.0.7", 18, 1.1e9, 130),
}
# how each service's CPU moves tick by tick
DRIFT = (6, -4, 3, -7, 2, 5, -3)
HEALTH = {"success": "Healthy", "warning": "Busy", "danger": "Saturated"}


def service(key: str, cpu: int, version: str | None = None, requests: float | None = None) -> dict:
    name, default_version, _, memory, default_requests = SERVICES[key]
    status = "danger" if cpu >= 85 else "warning" if cpu >= 70 else "success"
    return {
        "id": key,
        "name": name,
        "version": version or default_version,
        "cpu": cpu,
        "status": status,
        "health": HEALTH[status],
        "memory": memory,
        "requests": requests if requests is not None else default_requests,
    }


class ReleaseFeed(BaseModel):
    services: list[dict] = [service(key, cpu) for key, (_, _, cpu, _, _) in SERVICES.items()]
    rollouts: list[dict] = [{"id": "R-1", "service": "billing", "name": "Billing", "version": "v3.0.7", "progress": 100, "status": "Live"}]
    incidents: list[dict] = [
        {"id": "INC-7", "text": "Elevated p99 latency on Search in eu-west-1", "status": "warning", "acknowledged": False},
        {"id": "INC-6", "text": "Billing webhooks retried after a provider timeout", "status": "accent", "acknowledged": True},
    ]
    last_deploy: str = (datetime.now(UTC) - timedelta(hours=3)).isoformat()
    healthy: str = ""
    open_incidents: int = 0


feed = ReleaseFeed()
session = transports.Session()
session.host(feed)
server = transports.Server(session)


def refresh_totals() -> None:
    healthy = sum(row["status"] == "success" for row in feed.services)
    feed.healthy = f"{healthy} of {len(feed.services)} services healthy"
    feed.open_incidents = sum(not row["acknowledged"] for row in feed.incidents)


refresh_totals()


def replace(rows: list[dict], key: str, **changes) -> list[dict]:
    return [{**row, **changes} if row["id"] == key else row for row in rows]


async def stream_release() -> None:
    """Service load moves every tick, rollouts advance and land, and a saturated service raises an
    incident."""
    tick = 0
    while True:
        await asyncio.sleep(2)
        tick += 1
        services = []
        for index, row in enumerate(feed.services):
            cpu = max(5, min(95, row["cpu"] + DRIFT[(tick + index) % len(DRIFT)]))
            services.append(service(row["id"], cpu, row["version"], round(row["requests"] * (1 + (cpu - row["cpu"]) / 200))))
        rollouts = []
        for rollout in feed.rollouts:
            if rollout["status"] == "Rolling out":
                progress = min(100, rollout["progress"] + 20)
                rollout = {**rollout, "progress": progress, "status": "Live" if progress == 100 else "Rolling out"}
                if progress == 100:
                    services = replace(services, rollout["service"], version=rollout["version"])
                    feed.last_deploy = datetime.now(UTC).isoformat()
            rollouts.append(rollout)
        feed.services, feed.rollouts = services, rollouts
        saturated = next((row for row in services if row["status"] == "danger"), None)
        if saturated and not any(row["text"].startswith(saturated["name"]) and not row["acknowledged"] for row in feed.incidents):
            number = max(int(row["id"].removeprefix("INC-")) for row in feed.incidents) + 1
            incident = {
                "id": f"INC-{number}",
                "text": f"{saturated['name']} is saturated at {saturated['cpu']}% CPU",
                "status": "danger",
                "acknowledged": False,
            }
            feed.incidents = [incident, *feed.incidents][:6]
        refresh_totals()


async def deploy(request):
    body = await request.json()
    logger.info("Deployment from browser: %s", body)
    key = body.get("service")
    version = (body.get("version") or "").strip()
    if key not in SERVICES or not version:
        return JSONResponse({"message": "Choose a service and a version to deploy."}, status_code=422)
    rollout = {
        "id": f"R-{max(int(row['id'].removeprefix('R-')) for row in feed.rollouts) + 1}",
        "service": key,
        "name": SERVICES[key][0],
        "version": version,
        "progress": 0,
        "status": "Rolling out",
    }
    feed.rollouts = [rollout, *feed.rollouts][:5]
    canary = f", canary at {body.get('traffic')}% of traffic" if body.get("canary") else ""
    notify = ", on-call notified" if body.get("notify") else ""
    return JSONResponse(
        {
            "message": (
                f"{rollout['id']}: {rollout['name']} {version} on {body.get('replicas')} replicas, "
                f"{body.get('strategy')}{canary}, from {body.get('scheduled')}{notify}."
            )
        }
    )


async def restart(request):
    key = request.path_params["id"]
    row = next((row for row in feed.services if row["id"] == key), None)
    if row is None:
        return JSONResponse({"message": f"No service {key}."}, status_code=404)
    feed.services = replace(feed.services, key, **service(key, 20, row["version"], row["requests"]))
    refresh_totals()
    return JSONResponse({"message": f"Restarted {row['name']}"})


async def acknowledge(request):
    key = request.path_params["id"]
    if not any(row["id"] == key for row in feed.incidents):
        return JSONResponse({"message": f"No incident {key}."}, status_code=404)
    feed.incidents = replace(feed.incidents, key, acknowledged=True, status="accent")
    refresh_totals()
    return JSONResponse({"message": f"Acknowledged {key}"})


service_card = (
    BpCard(
        element(
            "div",
            BpProgressCircle(size="lg").compute("value", item("cpu")).compute("status", item("status")),
            element(
                "dl",
                element("dt").text("CPU"),
                element("dd").compute("textContent", concat(item("cpu"), "%")),
                element("dt").text("Memory"),
                element("dd", BpFormatBytes(unit_display="short").compute("value", item("memory"))),
                element("dt").text("Req/s"),
                element("dd", BpFormatNumber(notation="compact").compute("textContent", item("requests"))),
            ),
            class_="service-body",
        ),
        class_="service",
    )
    .compute("data-id", item("id"))
    .child_in(
        "header",
        element(
            "div",
            element("strong").compute("textContent", item("name")),
            BpBadge().compute("status", item("status")).compute("textContent", item("health")),
            class_="service-header",
        ),
    )
    .child_in(
        "footer",
        element(
            "div",
            BpTag(readonly=True).compute("textContent", item("version")),
            BpButton(action="secondary")
            .text("Restart")
            .on(
                "click",
                Sequence(
                    CallEndpoint("POST", concat("/api/services/", item("id"), "/restart"), result="restarted"),
                    Invoke(by_id("toast"), "showPopover"),
                ),
            ),
            class_="service-footer",
        ),
    )
)

services = element(
    "section",
    Row(
        BpIcon(shape="success", status="success"),
        element("span").bind("textContent", "healthy"),
        element("span", class_="muted").text("· last deploy"),
        BpFormatRelativeTime(sync=True).text(feed.last_deploy).bind("textContent", "last_deploy"),
        gap=".5rem",
        class_="summary",
    ),
    element("div", Each(service_card, field="services", key="id"), id="services", class_="services"),
    element("h3").text("Rollouts"),
    element(
        "div",
        Each(
            element(
                "div",
                element("strong").compute("textContent", concat(item("id"), " · ", item("name"), " ", item("version"))),
                BpProgressBar(max=100).compute("value", item("progress")).compute("status", cond(eq(item("status"), "Live"), "success", "accent")),
                BpBadge().compute("status", cond(eq(item("status"), "Live"), "success", "accent")).compute("textContent", item("status")),
                class_="rollout",
            ).compute("data-id", item("id")),
            field="rollouts",
            key="id",
        ),
        id="rollouts",
        class_="rollouts",
    ),
    class_="panel",
)


def labelled(label: str, control, message=None, **field_props):
    return BpField(element("label").text(label), control, *([message] if message is not None else []), **field_props)


deploy_form = element(
    "section",
    element(
        "div",
        labelled(
            "Service",
            BpSelect(*(BpOption(value=key).text(name) for key, (name, *_) in SERVICES.items()), id="deploy-service").bind(
                "value", "service", mode="two-way"
            ),
        ),
        labelled(
            "Version",
            BpInput(id="deploy-version", placeholder="v2.15.0").bind("value", "version", mode="two-way"),
            BpFieldMessage().text("The build tag to roll out"),
        ),
        labelled("Replicas", BpNumber(min=1, max=20).bind("value", "replicas", mode="two-way")),
        labelled("Start", BpDate(min=TODAY.isoformat()).bind("value", "scheduled", mode="two-way")),
        labelled(
            "Canary traffic",
            BpRange(min=0, max=100, step=5).bind("value", "traffic", mode="two-way"),
            BpFieldMessage().compute("textContent", concat(field("traffic"), "% of requests reach the new version first")),
        ),
        BpFieldset(
            element("label").text("Strategy"),
            element("label").text("Rolling"),
            BpRadio(value="rolling", checked=True).on("change", SetField("strategy", "rolling")),
            element("label").text("Blue-green"),
            BpRadio(value="blue-green").on("change", SetField("strategy", "blue-green")),
            layout="horizontal-inline",
        ),
        labelled("Canary release", BpSwitch().bind("checked", "canary", mode="two-way"), layout="horizontal-inline"),
        labelled("Notify on-call", BpCheckbox().bind("checked", "notify", mode="two-way"), layout="horizontal-inline"),
        labelled("Change notes", BpTextarea(rows=3).bind("value", "notes", mode="two-way"), class_="wide"),
        class_="form-grid",
    ),
    Row(
        BpButton(id="deploy", action="primary")
        .text("Deploy")
        .on(
            "click",
            Sequence(
                CallEndpoint(
                    "POST",
                    "/api/deployments",
                    obj(
                        {
                            "service": field("service"),
                            "version": field("version"),
                            "replicas": field("replicas"),
                            "scheduled": field("scheduled"),
                            "traffic": field("traffic"),
                            "strategy": field("strategy"),
                            "canary": field("canary"),
                            "notify": field("notify"),
                            "notes": field("notes"),
                        }
                    ),
                    result="deployed",
                ),
                Invoke(by_id("confirm"), "showPopover"),
            ),
        ),
        justify="end",
    ),
    class_="panel",
)

incidents = element(
    "section",
    Each(
        BpAlert(
            element("span").compute("textContent", concat(item("id"), " · ", item("text"))),
            BpButton(action="flat")
            .text("Acknowledge")
            .compute("disabled", item("acknowledged"))
            .on("click", CallEndpoint("POST", concat("/api/incidents/", item("id"), "/acknowledge"), result="acknowledged")),
        )
        .compute("status", item("status"))
        .compute("data-id", item("id")),
        field="incidents",
        key="id",
    ),
    id="incidents",
    class_="panel incidents",
)

confirm = (
    BpDialog(
        element("p", id="confirm-message").compute("textContent", field("deployed.body.message")), id="confirm", closable=True, modal=True, size="sm"
    )
    .child_in("header", element("h2").text("Deployment queued"))
    .child_in("footer", BpButton(id="confirm-close", action="primary").text("Watch the rollout").on("click", Invoke(by_id("confirm"), "hidePopover")))
)

toast = BpToast(id="toast", status="success", closable=True, position="bottom-end").compute("textContent", field("restarted.body.message"))

page = App(
    Nav(
        Row(element("strong", class_="brand").text("Release control"), BpTag(status="accent", readonly=True).text("production"), gap=".75rem"),
        element("label", element("span").text("Dark theme"), BpSwitch(id="dark").bind("checked", "dark", mode="two-way"), class_="dark-toggle"),
    ),
    Body(
        Main(
            BpAlert(
                element("span", class_="wrap").text(
                    "Service health, rollouts and incidents stream from Python; every control is a typed Blueprint element."
                ),
                status="accent",
            ),
            BpTabs(
                # Blueprint's tabs are stateless: the application says which one is selected
                BpTabList(
                    BpTab().text("Services").compute("selected", eq(field("tab"), 0)).on("click", SetField("tab", 0)),
                    BpTab().text("Deploy").compute("selected", eq(field("tab"), 1)).on("click", SetField("tab", 1)),
                    BpTab()
                    .child(element("span").text("Incidents "), BpBadge(status="danger").bind("textContent", "open_incidents"))
                    .compute("selected", eq(field("tab"), 2))
                    .on("click", SetField("tab", 2)),
                    **{"aria-label": "Release control"},
                ),
                BpTabPanel(services),
                BpTabPanel(deploy_form),
                BpTabPanel(incidents),
            ),
            confirm,
            toast,
            class_="page",
        ),
    ),
).bind_root_class("wa-dark", "dark")

styles = """
<style>
  body { margin: 0; background: var(--bp-layer-background-100); color: var(--bp-text-color-500); font-family: var(--bp-text-font); }
  spa-nav { justify-content: space-between; }
  .dark-toggle { display: inline-flex; align-items: center; gap: .5rem; }
  /* shown without an invoking button to anchor to, so placed against the viewport */
  #toast { inset: auto 0 0 auto; }
  .brand { font-size: 1.1rem; white-space: nowrap; }
  .page { box-sizing: border-box; width: 100%; max-width: 72rem; margin: 0 auto; padding: 1.5rem 1rem; display: grid; grid-template-columns: minmax(0, 1fr); align-content: start; gap: 1rem; }
  .panel { display: grid; gap: 1rem; padding-block: 1rem; }
  .summary { color: var(--bp-text-color-500); }
  .muted { color: var(--bp-text-color-400); }
  .wrap { white-space: normal; }
  .services { display: grid; grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr)); gap: 1rem; }
  .service-header, .service-footer { display: flex; align-items: center; justify-content: space-between; gap: .5rem; }
  .service-body { display: flex; align-items: center; gap: 1.25rem; }
  .service-body dl { display: grid; grid-template-columns: auto 1fr; gap: .25rem .75rem; margin: 0; }
  .service-body dt { color: var(--bp-text-color-400); }
  .service-body dd { margin: 0; font-variant-numeric: tabular-nums; white-space: nowrap; }
  h3 { margin: 0; }
  .rollouts, .incidents { display: grid; gap: .5rem; }
  .rollout { display: grid; grid-template-columns: minmax(12rem, auto) 1fr auto; align-items: center; gap: 1rem; }
  .incidents bp-alert { display: block; }
  .form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem 1.5rem; }
  .form-grid .wide { grid-column: 1 / -1; }
  @media (max-width: 720px) {
    .form-grid { grid-template-columns: 1fr; }
    .rollout { grid-template-columns: 1fr; }
  }
</style>
"""

app = serve(
    page,
    packages=[package],
    wire="transports",
    routes=[
        WebSocketRoute("/ws", transports.ws_endpoint(server)),
        Route("/api/deployments", deploy, methods=["POST"]),
        Route("/api/services/{id}/restart", restart, methods=["POST"]),
        Route("/api/incidents/{id}/acknowledge", acknowledge, methods=["POST"]),
    ],
    background=[transports.autosync(server), stream_release()],
    store={
        "dark": False,
        "tab": 0,
        "service": "api",
        "version": "v2.15.0",
        "replicas": "6",
        "scheduled": (TODAY + timedelta(days=1)).isoformat(),
        "traffic": "10",
        "strategy": "rolling",
        "canary": True,
        "notify": False,
        "notes": "",
        "deployed": {"body": {"message": ""}},
        "restarted": {"body": {"message": ""}},
        "acknowledged": {},
    },
    head=styles,
    title="spaday-blueprint example",
)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8023)
