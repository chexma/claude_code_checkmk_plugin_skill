# Dynamic Configuration Connector API (DCD)

> **CheckMK 2.5, commercial editions only (Pro/Ultimate/Cloud)** — not available in the Community edition (formerly Raw). Listed in the 2.5 Sphinx docs (*Help > Plug-in API references > Dynamic configuration connector*) as `cmk.nonfree.pro.dcd.connector_api`. It is **not versioned** (no `v1`) and carries no stability promise. Expect breaking changes between releases and tell the user before recommending it.

## Purpose

The Dynamic Configuration Daemon (DCD) creates, updates and deletes hosts automatically from external sources (piggyback data, cloud inventories, the metric backend, …). A *connector* is the plug-in that talks to one such source. This API covers the objects a connector passes between its two execution phases.

For most "create hosts automatically" needs, prefer the built-in **piggyback connector** (see `piggyback_api.md`), or the REST API (`rest_api.md`, including the unstable `dcd_metric_backend` endpoints). Write your own connector only when neither fits.

## Two-Phase Model

| Phase | Runs on | Job |
|---|---|---|
| Phase 1 | Site where the connection is configured to run | Collect data from the source → return a `Phase1Result` wrapping a `ConnectorObject` |
| Phase 2 | Central site | Receive the (serialized) `Phase1Result`, compute host changes, apply them via the Setup API |

`ConnectorObject`s are serialized between sites, so they may only contain data that `ast.literal_eval()` can handle (dicts, lists, strings, numbers, …).

## Public Names (`cmk.nonfree.pro.dcd.connector_api`)

| Name | Kind | Purpose |
|---|---|---|
| `ConnectorObject` | ABC | Base class for your transport object. Implement `_serialize_attributes()` and the classmethod `deserialize_attributes(serialized)`; override `is_empty()` if needed |
| `connector_object_registry` | Registry | Register your `ConnectorObject` subclass (`@connector_object_registry.register`) so that `ConnectorObject.deserialize()` can find it by class name |
| `Phase1Result` | Class | `Phase1Result(connector_object, status)` — result of phase 1 plus execution status |
| `NullObject` | `ConnectorObject` | "Nothing collected" |
| `FailedToContactRemoteSite` | `ConnectorObject` | Remote site was not reachable |

```python
from collections.abc import Mapping, Sequence
from typing import Self

from cmk.nonfree.pro.dcd.connector_api import ConnectorObject, connector_object_registry


@connector_object_registry.register
class MyHostsObject(ConnectorObject):
    def __init__(self, hosts: Sequence[str]) -> None:
        self.hosts = list(hosts)

    @classmethod
    def deserialize_attributes(cls, serialized: dict) -> Self:
        return cls(serialized["hosts"])

    def _serialize_attributes(self) -> Mapping[str, Sequence[str] | int]:
        return {"hosts": self.hosts}

    def is_empty(self) -> bool:
        return not self.hosts
```

## Writing a Connector

The connector class itself is **not** part of the documented API. It derives from `cmk.nonfree.pro.dcd.connector_backend.Connector` and uses the internal modules `cmk.nonfree.pro.dcd.config` and `cmk.nonfree.pro.dcd.site_api`. The site ships a minimal example to copy from:

```
~/lib/python3/cmk/nonfree/pro/dcd/plugins/connectors/example_connector.py
```

What a connector implements, based on that example:

| Member | Purpose |
|---|---|
| `name()` (classmethod) | Connector ID; must match the name of its config class |
| `_execution_interval()` | Seconds to sleep between runs |
| `_execute_phase1()` | Collect from the source → `Phase1Result` |
| `_get_site_changes(phase1_result)` | Return a `ChangeBatch` (hosts to add, modify, delete) or `None` |
| `_execute_phase2(phase1_result)` | Apply the changes |
| `load_config()` | (Re)load the connection's configuration |

- DCD loads connector plug-ins from the namespace `cmk.nonfree.pro.dcd.plugins.connectors`. Local plug-ins go in `~/local/lib/python3/cmk/nonfree/pro/dcd/plugins/connectors/`.
- Logs: `~/var/log/dcd.log`. Restart the daemon after changes: `omd restart dcd`.
- A connection also needs a Setup GUI form to configure it. The example connector doesn't include one, and there is no public API for it. This is one more reason to try the piggyback connector first.

## 2.4 → 2.5

The commercial Python namespace changed from `cmk.cee.*` to `cmk.nonfree.pro.*` / `cmk.nonfree.ultimate.*` in 2.5. The top-level package `cmk.cee` no longer exists. Connectors written against 2.4 import paths must be updated.

This does **not** affect the Bakery API v1 plugin location `cmk/base/cee/plugins/bakery/` (`cmk.base.cee…`). That is a different package, and 2.5 still loads it for compatibility (see `bakery_api.md`).
