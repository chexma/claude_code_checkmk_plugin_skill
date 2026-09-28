# CheckMK REST API (v1 and unstable)

> **CheckMK 2.5**: the REST API ships in two versions side by side. `v1` is stable and backwards compatible within a CheckMK major version. `unstable` holds experimental features and backports — its endpoints "may be removed or modified at any time without prior notice and should only be used for testing and development purposes" (upstream versioning note). Mention this to the user before building production automation on an `unstable` endpoint.

This file covers the REST API as a *client* — e.g. for automation scripts, piggyback host creation, or reading CheckMK data from a special agent. It is not a plugin API; for writing check plugins see `agent_based_api.md`.

## Contents

- [Versioning](#versioning)
- [Documentation URLs (inside CheckMK)](#documentation-urls-inside-checkmk)
- [Authentication](#authentication)
- [Client Basics](#client-basics)
- [New in unstable (CheckMK 2.5.0)](#new-in-unstable-checkmk-250)
- [Changes to Shared Endpoints](#changes-to-shared-endpoints)
- [Example: Create Piggyback Hosts (v1, stable)](#example-create-piggyback-hosts-v1-stable)
- [Checking What Changed in a New Build](#checking-what-changed-in-a-new-build)

## Versioning

| Version | Base URL | Status |
|---|---|---|
| `v1` | `https://<server>/<site>/check_mk/api/v1` | Stable (217 endpoints in 2.5.0) |
| `unstable` | `https://<server>/<site>/check_mk/api/unstable` | Experimental — superset of v1 plus 50 new endpoints |
| `1.0` (legacy) | `https://<server>/<site>/check_mk/api/1.0` | Old spelling of v1; still works, but use `v1` in new code |

- Versioning covers the whole API, not individual endpoints. Only the major number is used (`v1`, `v2`, …); compatible changes land in the current version without a bump.
- All published major versions stay supported for the whole CheckMK major version, so patch updates do not break `v1` scripts.
- **Every v1 endpoint is also available under `unstable`** (same paths).
- **Prefer `v1` for each call.** Use the `unstable` base URL only for the endpoints that exist only there, so the rest of the script stays on the stable version. For example, keep two base URLs in the client instead of switching everything to `unstable`.
- Endpoints new in unstable carry the marker `` `NEW`: This endpoint is new in this API version. `` in their description.

## Documentation URLs (inside CheckMK)

Replace `v1` with `unstable` for the unstable spec:

```
# ReDoc reference
https://<server>/<site>/check_mk/api/v1/doc/
https://<server>/<site>/check_mk/api/unstable/doc/

# Swagger UI (interactive)
https://<server>/<site>/check_mk/api/v1/ui/
https://<server>/<site>/check_mk/api/unstable/ui/

# Raw OpenAPI spec (needs authentication, see below)
https://<server>/<site>/check_mk/api/unstable/openapi-doc.yaml
https://<server>/<site>/check_mk/api/unstable/openapi-doc.json
```

The spec endpoints return `401` without credentials. The ReDoc page works in the browser because it reuses the GUI session cookie. On the CheckMK server the pre-generated specs also live on disk, readable without credentials:

```
~/share/doc/check_mk/rest-api/spec/doc.spec               # v1
~/share/doc/check_mk/rest-api/spec/unstable-doc.spec      # unstable
```

(These are Python-literal dicts, not JSON — load them with `ast.literal_eval`.)

## Authentication

Methods in order of precedence (the first one that succeeds wins):

| Method | Header | Notes |
|---|---|---|
| Bearer (`headerAuth`) | `Authorization: Bearer <user> <secret>` | Username and password/automation secret separated by a **space**. Preferred for scripts |
| Web server (`webserverAuth`) | HTTP Basic/Digest | Only if the site's Apache is configured for it |
| Cookie | GUI session | Used automatically in the browser (ReDoc/Swagger) |

Any user can use the API — automation users or GUI users — as long as it has the needed permissions. Each endpoint's description lists its permissions (e.g. `wato.edit`, `general.see_availability`).

## Client Basics

```python
import requests

API_URL = "https://mycmk.example.com/mysite/check_mk/api"
V1 = f"{API_URL}/v1"              # default for everything
UNSTABLE = f"{API_URL}/unstable"  # only for endpoints that exist only there

session = requests.Session()
# New 2.5 sites have no default "automation" user (Werk #17344): create one
session.headers["Authorization"] = "Bearer <automation-user> <secret>"
session.headers["Accept"] = "application/json"


def get(path: str, *, base: str = V1, **params):
    resp = session.get(f"{base}{path}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()
```

Conventions that apply to both versions:

- **Collections**: `GET /domain-types/<type>/collections/all` → envelope with a `value` list. **Single objects**: `GET /objects/<type>/<id>`.
- **Actions**: `POST|PUT|PATCH /domain-types/<type>/actions/<action>/invoke`.
- **List query parameters** are sent as repeated keys: `?host_names=a&host_names=b` (`requests` does this for a Python list).
- **Changing an object** (e.g. `PUT /objects/host_config/{host_name}`) needs an `If-Match` header with the object's ETag from a previous `GET` of that object. The header is always required; the value is only compared when ETag validation is enabled on the site.
- **Config changes** (hosts, rules, relays, OTel configs, …) are *pending* until activated: `POST /domain-types/activation_run/actions/activate-changes/invoke`.
- Clients without `PUT`/`DELETE` can send `POST` plus `X-HTTP-Method-Override: PUT|DELETE`.
- Undocumented behaviour may change without a version bump — rely only on documented fields.

## New in `unstable` (CheckMK 2.5.0)

Compared with the v1 spec of the same build (checked on 2.5.0p14): 50 extra endpoints, nothing removed. Edition availability is part of each endpoint's description; **"commercial"** means not available in Checkmk Raw/Community.

### Dashboards (14 endpoints)

Two dashboard types: `dashboard_relative_grid` (classic layout, all editions) and `dashboard_responsive_grid` (commercial editions).

| Method | Path | Purpose |
|---|---|---|
| POST | `/domain-types/dashboard_relative_grid/collections/all` | Create relative-grid dashboard |
| GET / PUT | `/objects/dashboard_relative_grid/{dashboard_id}` | Show / edit |
| POST | `/domain-types/dashboard_relative_grid/actions/clone/invoke` | Clone as relative dashboard |
| POST | `/domain-types/dashboard_responsive_grid/collections/all` | Create responsive-grid dashboard |
| GET / PUT | `/objects/dashboard_responsive_grid/{dashboard_id}` | Show / edit |
| POST | `/domain-types/dashboard_responsive_grid/actions/clone/invoke` | Clone as responsive (relative ones cannot be cloned into responsive) |
| DELETE | `/objects/dashboard/{dashboard_id}` | Delete (either type) |
| GET | `/domain-types/dashboard_metadata/collections/all` | List dashboards the user may see |
| GET | `/objects/dashboard_metadata/{dashboard_id}` | Metadata of one dashboard |
| GET | `/objects/constant/dashboard` | Layout constraints (sizes, limits) |
| POST | `/domain-types/dashboard/actions/compute-widget-attributes/invoke` | Compute attributes for a widget `content` |
| POST | `/domain-types/dashboard/actions/compute-top-list/invoke` | Evaluate a top-list widget (`content`, `context`) — commercial |

- Create/edit body (all required): `id`, `general_settings`, `filter_context`, `layout`, `widgets`.
- Clone body: `reference_dashboard_id` (req), `dashboard_id` (req), `reference_dashboard_owner` (empty string = built-in dashboard), `general_settings`.
- Object endpoints take an optional `owner` query parameter to address another user's dashboard.
- Permissions: `general.edit_dashboards`, optionally `general.force_dashboards`.

### Availability (4 endpoints)

| Method | Path | Required query params |
|---|---|---|
| GET | `/domain-types/host_availability/collections/all` | `time_range_from`, `time_range_until` (optional `site_id`) |
| GET | `/objects/host_availability/{host_name}` | `time_range_from`, `time_range_until` (optional `site_id`) |
| GET | `/domain-types/service_availability/collections/all` | `site_id`, `host_name`, `time_range_from`, `time_range_until` |
| GET | `/objects/host/{host_name}/service_availability/{service_name}` | `time_range_from`, `time_range_until` (optional `site_id`) |

Time values are ISO 8601 **with timezone**, e.g. `2026-09-01T00:00:00+00:00`. Permission: `general.see_availability`.

```python
data = get(
    "/objects/host_availability/myhost",
    base=UNSTABLE,
    time_range_from="2026-09-01T00:00:00+00:00",
    time_range_until="2026-09-28T00:00:00+00:00",
)
```

### Historical Event Console events (2 endpoints)

| Method | Path | Params |
|---|---|---|
| GET | `/domain-types/historical_event/collections/all` | optional: `site_id`, `event_ids` (list of int), `host`, `application`, `state` (`ok`/`warning`/`critical`/`unknown`), `phase` (`open`/`ack`/`closed`/`delayed`/`counting`), `query` (Livestatus filter expression as JSON) |
| GET | `/objects/historical_event/{event_id}` | required: `site_id` |

`query` uses the same filter-expression syntax as other status queries, e.g. `{"op": "=", "left": "event_host", "right": "host1"}`.

### HW/SW Inventory (1 endpoint)

| Method | Path | Params |
|---|---|---|
| GET | `/domain-types/inventory/collections/all` | required: `host_names` (list) |

Returns the inventory trees of the given hosts — useful to verify an `InventoryPlugin` (see `inventory_api.md`) without the GUI.

```python
trees = get("/domain-types/inventory/collections/all", base=UNSTABLE, host_names=["host1", "host2"])
```

### Relays (6 endpoints) — Ultimate / Ultimate MT / Cloud

| Method | Path | Purpose |
|---|---|---|
| GET | `/domain-types/relay/collections/all` | List relays |
| POST | `/domain-types/relay/collections/all` | Store a relay configuration |
| GET / PUT / DELETE | `/objects/relay/{relay_id}` | Show / edit / delete |
| POST | `/domain-types/relay_registration_token/collections/all` | Create registration token (`expires_at`, default +1 h) |

Body: `relay_id` (create only), `alias`, `siteid`, `num_fetchers`, `log_level` (`CRITICAL`/`ERROR`/`WARNING`/`INFO`/`DEBUG`) — all required; optional `num_checkhelpers`. Creating the config does **not** deploy a working relay; the relay itself still has to be registered with a token. Permissions: `relay.manage_any_relay` / `relay.view_any_relay`.

### OpenTelemetry (11 endpoints) — Ultimate / Ultimate MT

| Method | Path | Purpose |
|---|---|---|
| GET | `/domain-types/otel_collector/actions/get/invoke?site_id=…` | Collector activation state |
| PUT | `/domain-types/otel_collector/actions/update/invoke` | Enable/disable collector (`site_id`, `activation`) |
| GET / POST | `/domain-types/otel_collector_config_prom_scrape/collections/all` | List / create Prometheus scrape configs |
| GET / PUT / DELETE | `/objects/otel_collector_config_prom_scrape/{config_id}` | Show / update / delete |
| GET | `/domain-types/otel_collector_config_receivers/collections/all` | List receiver configs |
| GET / PUT / DELETE | `/objects/otel_collector_config_receivers/{config_id}` | Show / update / delete |

- Config body: `id`, `title`, `disabled`, `site` (list) required; optional `comment`, `docu_url`, plus `prometheus_scrape_configs` (scrape) or `receiver_protocol_grpc` / `receiver_protocol_http` (receivers).
- The receivers family has no create (`POST`) endpoint in 2.5.0p14.
- Permissions: `wato.otel_collector` (write), `wato.read_otel_collector` (read).

### Metric backend (6 endpoints)

| Method | Path | Editions | Purpose |
|---|---|---|---|
| GET | `/domain-types/metric_backend/actions/get/invoke?site_id=…` | Ultimate, Ultimate MT | Activation state |
| PATCH | `/domain-types/metric_backend/actions/update/invoke` | Ultimate, Ultimate MT | Partial update (`site_id`, `config`); omitted fields keep their value, switching `type` from disabled to enabled fills suggested defaults |
| GET / POST | `/domain-types/dcd_metric_backend/collections/all` | Ultimate, Ultimate MT, Cloud | List / create DCD connections using the metric backend connector |
| GET / DELETE | `/objects/dcd_metric_backend/{dcd_id}` | Ultimate, Ultimate MT, Cloud | Show / delete |

DCD create body: `dcd_id`, `title`, `site`, `connector` required; optional `comment`, `documentation_url`, `disabled`. Permission: `wato.dcd_connections` (+ `wato.edit` for changes).

### GUI helpers (6 endpoints)

| Method | Path | Purpose |
|---|---|---|
| GET | `/domain-types/graph_timerange/collections/all` | Configured graph time ranges |
| GET | `/objects/graph_timerange/{index}` | One time range |
| GET | `/domain-types/visual_filter/collections/all` | All visual filter definitions |
| GET | `/domain-types/sidebar_element/collections/all` | Sidebar snap-in elements |
| DELETE | `/objects/user_message/{message_id}` | Delete a user message |
| POST | `/objects/user_message/{message_id}/actions/acknowledge/invoke` | Acknowledge a user message |

## Changes to Shared Endpoints

- `host_config` endpoints (`GET/POST /domain-types/host_config/collections/all`, `/objects/host_config/{host_name}`, bulk-create/-update, clusters, nodes) are reimplemented in `unstable` on a new (pydantic-based) framework. Field names are the same (`host_name`, `folder`, `attributes`; query params `effective_attributes`, `include_links`, `fields`, `hostnames`, `site`), but validation and error messages may differ from v1.
- Deprecated in both versions (Werk #17003): the `GET` variants of the status queries below. Use `POST` on the same path instead, with the filter (`query`, `columns`, …) in the JSON body:
  - `/domain-types/host/collections/all` ("Show hosts of specific condition")
  - `/domain-types/service/collections/all` ("Show all monitored services")
  - `/objects/host/{host_name}/collections/services`

## Example: Create Piggyback Hosts (v1, stable)

```python
resp = session.post(
    f"{V1}/domain-types/host_config/collections/all",
    json={
        "folder": "/piggyback",
        "host_name": "vm-01",
        "attributes": {"tag_agent": "no-agent", "tag_piggyback": "piggyback"},
    },
    timeout=30,
)
resp.raise_for_status()
session.post(
    f"{V1}/domain-types/activation_run/actions/activate-changes/invoke",
    json={"redirect": False, "force_foreign_changes": False},
    timeout=60,
).raise_for_status()
```

## Checking What Changed in a New Build

To diff `v1` against `unstable` (or two builds) on a site:

```python
import ast

spec_dir = "/omd/sites/<site>/share/doc/check_mk/rest-api/spec"
load = lambda f: ast.literal_eval(open(f"{spec_dir}/{f}").read())
v1, un = load("doc.spec"), load("unstable-doc.spec")


def ops(spec):
    return {
        (m.upper(), p)
        for p, methods in spec["paths"].items()
        for m, op in methods.items()
        if isinstance(op, dict) and "responses" in op
    }


for method, path in sorted(ops(un) - ops(v1)):
    print(method, path)
```
