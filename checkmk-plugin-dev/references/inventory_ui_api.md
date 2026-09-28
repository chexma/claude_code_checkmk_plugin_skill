# Inventory UI API

> **CheckMK 2.5+, unstable**: `cmk.inventory_ui.v1_unstable` is a work-in-progress API and may still change. Timeline: see `SKILL.md` → *Stability and timeline*. Mention this to the user before recommending it for production plugins. No 2.4 equivalent — 2.4 has no way to customize how inventory data is *displayed*, only what's collected (see `inventory_api.md`).

## Purpose

`inventory_api.md` covers *collecting* HW/SW inventory data (`InventoryPlugin`, `Attributes`, `TableRow` — unchanged in 2.5). This API covers *displaying* that data: customizing how an inventory tree node renders in the GUI (field types, number formatting, colors, sortable/filterable table views).

Use this when the default rendering of inventory attributes/tables (plain text) isn't good enough — e.g. you want a boolean shown as "Enabled"/"Disabled" instead of `True`/`False`, a byte count rendered with `IECNotation`, or a filterable table view.

## Location and Registration

File: `~/local/lib/python3/cmk_addons/plugins/<family>/inventory_ui/<name>.py` (built-in examples: `~/lib/python3/cmk/plugins/collection/inventory_ui/`).

Discovery is by variable name prefix — `node_<name>` for a `Node` (the only plug-in type in `entry_point_prefixes()`):

```python
node_myapp = Node(name="myapp", ...)
```

## Core Components

### Field Types (how a single value renders)

All fields take `title` positionally; everything else is keyword-only. `style` is a callable `value -> Iterable[Alignment | BackgroundColor | LabelColor]`.

| Class | Parameters |
|---|---|
| `BoolField` | `title`, `render_true=Label("Yes")`, `render_false=Label("No")` (`Label` or `str`), `style` |
| `TextField` | `title`, `render=` (`str -> Label \| str`), `style`, `sort_key=` (`str -> Comparable`, enables `<`/`>` comparisons) |
| `NumberField` | `title`, `render=` a `Unit(...)` or a callable (`int \| float -> Label \| str`), `style` |
| `ChoiceField` | `title`, `mapping={raw_value: Label \| str}` (required, non-empty), `style` |

### Structure

| Class | Parameters |
|---|---|
| `Node` | kw-only: `name` (unique, required), `title`, `path` (sequence of str), `attributes={key: field}`, `table=Table()` |
| `Table` | `columns={key: field}`, `view=None` |
| `View` | kw-only: `name` (unique), `title` — adds an "Open this table for filtering / sorting" view |

### Number Formatting (for `NumberField`)

Wrap a notation in `Unit(notation, precision=AutoPrecision(2))`:

- Notations: `DecimalNotation`, `SINotation`, `IECNotation`, `StandardScientificNotation`, `EngineeringScientificNotation`, `TimeNotation`, `AgeNotation` (each takes a symbol, e.g. `IECNotation("B")`; `TimeNotation()`/`AgeNotation()` take none).
- Precision: `AutoPrecision(digits)`, `StrictPrecision(digits)`.

These mirror the equivalent classes in the Graphing API (`graphing_api.md`) — same concepts, applied to inventory display instead of metric graphs.

### Styling

- `Alignment`: `LEFT`, `CENTER`, `RIGHT`
- `BackgroundColor`, `LabelColor`: 32 light/dark color options each (e.g. `LIGHT_RED`, `RED`, `DARK_RED`, …)
- `Label`, `Title`: localizable text, same pattern as `cmk.rulesets.v1.Title`/`Label`

## Example

```python
#!/usr/bin/env python3
"""Custom inventory display for MyApp modules table."""
from cmk.inventory_ui.v1_unstable import (
    Alignment, AutoPrecision, BoolField, IECNotation, Label, Node, NumberField,
    Table, TextField, Title, Unit, View,
)

node_myapp_modules = Node(
    name="myapp_modules",
    path=["software", "applications", "myapp", "modules"],
    title=Title("MyApp Modules"),
    table=Table(
        columns={
            "name": TextField(Title("Module")),
            "enabled": BoolField(
                Title("Enabled"),
                render_true=Label("Enabled"),
                render_false=Label("Disabled"),
            ),
            "size_bytes": NumberField(
                Title("Size"),
                render=Unit(IECNotation("B"), AutoPrecision(2)),
                style=lambda _: [Alignment.RIGHT],
            ),
        },
        view=View(name="invmyappmodules", title=Title("MyApp modules")),
    ),
)
```

## Best Practices

1. **Only add a `Node` when the default rendering is insufficient** — most `Attributes`/`TableRow` data from `inventory_api.md` displays fine without one.
2. **Keep the path in sync** with the `path=[...]` used by the corresponding `InventoryPlugin`/`TableRow` in `inventory_api.md` — this API only changes rendering, not the data itself.
3. **Treat it as unstable**: check the changelog before relying on it beyond 2.5 (see `SKILL.md` → *Stability and timeline*).

## Related Topics

- **Collecting the underlying data** → `inventory_api.md` (`InventoryPlugin`, `Attributes`, `TableRow` — unchanged in 2.5)
- **Equivalent number-formatting concepts for graphs** → `graphing_api.md`
