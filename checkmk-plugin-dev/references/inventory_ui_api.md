# Inventory UI API

> **CheckMK 2.5+, unstable**: `cmk.inventory_ui.v1_unstable` is a work-in-progress API and may change before it stabilizes (planned for 2.6, per Werk #18600). Mention this to the user before recommending it for production plugins. No 2.4 equivalent — 2.4 has no way to customize how inventory data is *displayed*, only what's collected (see `inventory_api.md`).

## Purpose

`inventory_api.md` covers *collecting* HW/SW inventory data (`InventoryPlugin`, `Attributes`, `TableRow` — unchanged in 2.5). This API covers *displaying* that data: customizing how an inventory tree node renders in the GUI (field types, number formatting, colors, sortable/filterable table views).

Use this when the default rendering of inventory attributes/tables (plain text) isn't good enough — e.g. you want a boolean shown as "Enabled"/"Disabled" instead of `True`/`False`, a byte count rendered with `IECNotation`, or a filterable table view.

## Registration Pattern

Like other plugin types, discovery is by variable name prefix — `node_<name>` for a `Node`:

```python
node_myapp = Node(...)
```

## Core Components

### Field Types (how a single value renders)

| Class | Renders |
|---|---|
| `BoolField` | Boolean, with customizable true/false labels |
| `TextField` | String, with optional custom render function and sort key |
| `NumberField` | Numeric value, with configurable notation/precision/styling |
| `ChoiceField` | Enum-like value mapped to a readable label |

### Structure

| Class | Purpose |
|---|---|
| `Node` | An inventory tree entry: attributes + tables + path |
| `Table` | Columnar data, optionally with filtered/sorted `View`s |
| `View` | An interactive, filterable/sortable table view |

### Number Formatting (for `NumberField`)

Notations: `SINotation`, `IECNotation`, `DecimalNotation`, `TimeNotation`, `AgeNotation`, `StandardScientificNotation`, `EngineeringScientificNotation`.
Precision control: `StrictPrecision`, `AutoPrecision`.

These mirror the equivalent classes in the Graphing API (`graphing_api.md`) — same concepts, applied to inventory display instead of metric graphs.

### Styling

- `Alignment`: `LEFT`, `CENTER`, `RIGHT`
- `BackgroundColor`, `LabelColor`: 32 light/dark color options
- `Label`, `Title`: localizable text, same pattern as `cmk.rulesets.v1.Title`/`Label`

## Example

```python
#!/usr/bin/env python3
"""Custom inventory display for MyApp modules table."""
from cmk.inventory_ui.v1_unstable import (
    Node, Table, BoolField, TextField, NumberField, Title, Label,
)

node_myapp_modules = Node(
    path=["software", "applications", "myapp", "modules"],
    title=Title("MyApp Modules"),
    table=Table(
        columns={
            "name": TextField(title=Title("Module")),
            "enabled": BoolField(
                title=Title("Enabled"),
                render_true=Label("Enabled"),
                render_false=Label("Disabled"),
            ),
            "size_bytes": NumberField(title=Title("Size")),
        },
    ),
)
```

## Best Practices

1. **Only add a `Node` when the default rendering is insufficient** — most `Attributes`/`TableRow` data from `inventory_api.md` displays fine without one.
2. **Keep the path in sync** with the `path=[...]` used by the corresponding `InventoryPlugin`/`TableRow` in `inventory_api.md` — this API only changes rendering, not the data itself.
3. **Treat it as unstable**: don't ship this in a plugin meant to run unmodified past the 2.6 stabilization without checking the changelog first.

## Related Topics

- **Collecting the underlying data** → `inventory_api.md` (`InventoryPlugin`, `Attributes`, `TableRow` — unchanged in 2.5)
- **Equivalent number-formatting concepts for graphs** → `graphing_api.md`
