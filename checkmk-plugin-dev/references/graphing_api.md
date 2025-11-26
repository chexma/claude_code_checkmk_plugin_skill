# Graphing API V1 Reference

## Location
`~/local/lib/python3/cmk_addons/plugins/<family>/graphing/`

## Complete Import Statement
```python
from cmk.graphing.v1 import Title

from cmk.graphing.v1.metrics import (
    Metric,
    Color,
    Unit,
    DecimalNotation,
    SINotation,
    IECNotation,
    StandardScientificNotation,
    EngineeringScientificNotation,
    TimeNotation,
)

from cmk.graphing.v1.graphs import (
    Graph,
    MinimalRange,
)

from cmk.graphing.v1.perfometers import (
    Perfometer,
    Bidirectional,
    Stacked,
    FocusRange,
    Closed,
    Open,
)

from cmk.graphing.v1.translations import (
    Translation,
    RenameTo,
    ScaleBy,
    RenameToAndScaleBy,
)
```

## Metric Definition

Define how metrics appear in graphs:

```python
metric_cpu_usage = Metric(
    name="cpu_usage",                              # Must match metric_name in check
    title=Title("CPU Usage"),
    unit=Unit(DecimalNotation("%")),
    color=Color.BLUE,
)

metric_memory_used = Metric(
    name="memory_used",
    title=Title("Memory Used"),
    unit=Unit(IECNotation("B")),                   # Bytes with Ki, Mi, Gi prefixes
    color=Color.GREEN,
)

metric_temperature = Metric(
    name="temperature",
    title=Title("Temperature"),
    unit=Unit(DecimalNotation("°C")),
    color=Color.ORANGE,
)
```

## Unit Notations

| Notation | Use Case | Example |
|----------|----------|---------|
| `DecimalNotation("")` | Pure number | "42" |
| `DecimalNotation("%")` | Percentage | "42.5%" |
| `DecimalNotation("°C")` | Temperature | "23.5°C" |
| `DecimalNotation("/s")` | Rate | "1000/s" |
| `SINotation("B")` | Bytes (1000-based) | "1.5 MB" |
| `IECNotation("B")` | Bytes (1024-based) | "1.5 MiB" |
| `SINotation("bit/s")` | Network bandwidth | "100 Mbit/s" |
| `SINotation("Hz")` | Frequency | "3.5 GHz" |
| `TimeNotation()` | Duration | "2h 30min" |

## Color Options

```python
Color.BLUE
Color.GREEN
Color.RED
Color.YELLOW
Color.ORANGE
Color.PURPLE
Color.PINK
Color.CYAN
Color.BROWN
Color.GRAY
Color.BLACK
Color.WHITE
Color.LIGHT_BLUE
Color.LIGHT_GREEN
Color.LIGHT_RED
Color.LIGHT_YELLOW
Color.LIGHT_ORANGE
Color.LIGHT_PURPLE
Color.LIGHT_PINK
Color.LIGHT_CYAN
Color.LIGHT_BROWN
Color.LIGHT_GRAY
Color.DARK_BLUE
Color.DARK_GREEN
Color.DARK_RED
Color.DARK_YELLOW
Color.DARK_ORANGE
Color.DARK_PURPLE
Color.DARK_PINK
Color.DARK_CYAN
Color.DARK_BROWN
Color.DARK_GRAY
```

## Graph Definition

Combine multiple metrics in one graph:

```python
graph_cpu_overview = Graph(
    name="cpu_overview",
    title=Title("CPU Overview"),
    simple_lines=[
        "cpu_user",
        "cpu_system",
        "cpu_iowait",
    ],
    minimal_range=MinimalRange(0, 100),
)

# With stacked areas
graph_memory = Graph(
    name="memory_usage",
    title=Title("Memory Usage"),
    compound_lines=[
        "memory_used",
        "memory_cached",
        "memory_buffers",
    ],
    simple_lines=[
        "memory_total",
    ],
    minimal_range=MinimalRange(0, None),  # None = auto-scale upper bound
)
```

### Graph Options
- `simple_lines` - Regular line plots
- `compound_lines` - Stacked area plots
- `optional` - Metrics shown if available (list of metric names)
- `conflicting` - Mutually exclusive metrics (list of metric names)
- `minimal_range` - Minimum Y-axis range

## Perfometer Definition

Bar display in service list:

### Simple Perfometer
```python
perfometer_cpu = Perfometer(
    name="cpu_usage",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["cpu_usage"],
)
```

### Stacked Perfometer
Multiple metrics stacked:

```python
perfometer_disk = Stacked(
    name="disk_io",
    lower=Perfometer(
        name="disk_read",
        focus_range=FocusRange(Closed(0), Open(100000000)),
        segments=["disk_read_throughput"],
    ),
    upper=Perfometer(
        name="disk_write",
        focus_range=FocusRange(Closed(0), Open(100000000)),
        segments=["disk_write_throughput"],
    ),
)
```

### Bidirectional Perfometer
For in/out metrics:

```python
perfometer_network = Bidirectional(
    name="network_io",
    left=Perfometer(
        name="net_in",
        focus_range=FocusRange(Closed(0), Open(1000000000)),
        segments=["if_in_octets"],
    ),
    right=Perfometer(
        name="net_out",
        focus_range=FocusRange(Closed(0), Open(1000000000)),
        segments=["if_out_octets"],
    ),
)
```

### Focus Range Boundaries
- `Closed(value)` - Fixed boundary (value cannot exceed)
- `Open(value)` - Soft boundary (can auto-scale beyond)

## Metric Translation

For renaming or scaling existing metrics:

```python
translation_legacy = Translation(
    name="legacy_cpu",
    check_commands=["legacy_check_cpu"],
    translations={
        "old_cpu_metric": RenameTo("cpu_usage"),
        "old_bytes": RenameToAndScaleBy("data_bytes", 1024),  # Multiply by 1024
    },
)
```

## Complete Example

```python
#!/usr/bin/env python3

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import Metric, Color, Unit, DecimalNotation, IECNotation
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.perfometers import Perfometer, FocusRange, Closed, Open

# Metric definitions
metric_cpu_user = Metric(
    name="cpu_user",
    title=Title("CPU User"),
    unit=Unit(DecimalNotation("%")),
    color=Color.BLUE,
)

metric_cpu_system = Metric(
    name="cpu_system",
    title=Title("CPU System"),
    unit=Unit(DecimalNotation("%")),
    color=Color.RED,
)

metric_cpu_total = Metric(
    name="cpu_total",
    title=Title("CPU Total"),
    unit=Unit(DecimalNotation("%")),
    color=Color.GREEN,
)

metric_memory_used = Metric(
    name="memory_used",
    title=Title("Memory Used"),
    unit=Unit(IECNotation("B")),
    color=Color.PURPLE,
)

# Graph combining metrics
graph_cpu = Graph(
    name="cpu_usage_graph",
    title=Title("CPU Usage"),
    compound_lines=["cpu_user", "cpu_system"],
    simple_lines=["cpu_total"],
    minimal_range=MinimalRange(0, 100),
)

# Perfometer for service list
perfometer_cpu = Perfometer(
    name="cpu_usage",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["cpu_total"],
)

perfometer_memory = Perfometer(
    name="memory_usage",
    focus_range=FocusRange(Closed(0), Open(1073741824)),  # 1 GiB soft limit
    segments=["memory_used"],
)
```

## Restart Requirements

After creating or modifying graphing files:
```bash
omd restart apache
```

## Connecting Metrics from Check Plugin

In the check plugin, metrics are created with matching names:

```python
def check_cpu(section):
    # These metric names must match the metric definitions
    yield Metric("cpu_user", user_percent)
    yield Metric("cpu_system", system_percent)
    yield Metric("cpu_total", total_percent)
    
    # Or via check_levels
    yield from check_levels(
        total_percent,
        metric_name="cpu_total",  # Links to metric_cpu_total definition
        # ...
    )
```

## Default Behavior Without Graphing Definition

If no metric definition exists:
- Metric name becomes title (underscores → spaces, capitalized)
- Random color assigned
- No unit displayed
- Individual graph per metric (no combining)
- No perfometer

Graphing definitions provide:
- Proper titles and units
- Consistent colors
- Combined graphs
- Perfometer display
