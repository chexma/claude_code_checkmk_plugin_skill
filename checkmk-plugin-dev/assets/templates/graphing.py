#!/usr/bin/env python3
"""
Graphing/Metrics Definition Template
====================================
Location: ~/local/lib/python3/cmk_addons/plugins/<family>/graphing/

Defines how metrics appear in graphs and perfometers.
After changes: omd restart apache
"""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import (
    Metric,
    Color,
    Unit,
    DecimalNotation,
    IECNotation,
    SINotation,
)
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.perfometers import (
    Perfometer,
    Bidirectional,
    Stacked,
    FocusRange,
    Closed,
    Open,
)


# =============================================================================
# METRIC DEFINITIONS
# Names must match metric_name in check plugin
# =============================================================================

metric_mycheck_value = Metric(
    name="mycheck_value",
    title=Title("My Check Value"),
    unit=Unit(DecimalNotation("%")),
    color=Color.BLUE,
)

metric_mycheck_count = Metric(
    name="mycheck_count",
    title=Title("Item Count"),
    unit=Unit(DecimalNotation("")),
    color=Color.GREEN,
)

metric_mycheck_bytes = Metric(
    name="mycheck_bytes",
    title=Title("Data Size"),
    unit=Unit(IECNotation("B")),    # KiB, MiB, GiB (1024-based)
    color=Color.PURPLE,
)

metric_mycheck_rate = Metric(
    name="mycheck_rate",
    title=Title("Transfer Rate"),
    unit=Unit(SINotation("B/s")),   # KB/s, MB/s, GB/s (1000-based)
    color=Color.ORANGE,
)


# =============================================================================
# GRAPH DEFINITIONS
# Combine multiple metrics into one graph
# =============================================================================

graph_mycheck_overview = Graph(
    name="mycheck_overview",
    title=Title("My Check Overview"),
    simple_lines=[
        "mycheck_value",
        "mycheck_count",
    ],
    minimal_range=MinimalRange(0, 100),
)

# Stacked area graph
graph_mycheck_stacked = Graph(
    name="mycheck_details",
    title=Title("My Check Details"),
    compound_lines=[          # Stacked areas
        "mycheck_bytes",
    ],
    simple_lines=[            # Regular lines on top
        "mycheck_rate",
    ],
    optional=[                # Show if available
        "mycheck_extra",
    ],
)


# =============================================================================
# PERFOMETER DEFINITIONS
# Bar display in service list
# =============================================================================

# Simple percentage perfometer
perfometer_mycheck = Perfometer(
    name="mycheck_value",
    focus_range=FocusRange(
        Closed(0),    # Fixed lower bound
        Closed(100),  # Fixed upper bound
    ),
    segments=["mycheck_value"],
)

# Perfometer with auto-scaling upper bound
perfometer_mycheck_bytes = Perfometer(
    name="mycheck_bytes",
    focus_range=FocusRange(
        Closed(0),
        Open(1073741824),  # 1 GiB soft limit (auto-scales beyond)
    ),
    segments=["mycheck_bytes"],
)

# Bidirectional perfometer (e.g., for in/out traffic)
# perfometer_mycheck_io = Bidirectional(
#     name="mycheck_io",
#     left=Perfometer(
#         name="mycheck_in",
#         focus_range=FocusRange(Closed(0), Open(1000000000)),
#         segments=["mycheck_bytes_in"],
#     ),
#     right=Perfometer(
#         name="mycheck_out",
#         focus_range=FocusRange(Closed(0), Open(1000000000)),
#         segments=["mycheck_bytes_out"],
#     ),
# )

# Stacked perfometer (multiple metrics in one bar)
# perfometer_mycheck_stacked = Stacked(
#     name="mycheck_stacked",
#     lower=Perfometer(
#         name="mycheck_lower",
#         focus_range=FocusRange(Closed(0), Closed(100)),
#         segments=["mycheck_value"],
#     ),
#     upper=Perfometer(
#         name="mycheck_upper", 
#         focus_range=FocusRange(Closed(0), Closed(100)),
#         segments=["mycheck_count"],
#     ),
# )
