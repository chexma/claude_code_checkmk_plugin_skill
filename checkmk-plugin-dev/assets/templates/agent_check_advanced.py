#!/usr/bin/env python3
"""
Advanced Agent-Based Check Plugin Template
==========================================
Features: Items, Parameters (Ruleset), Metrics, check_levels()

Location: ~/local/lib/python3/cmk_addons/plugins/<family>/agent_based/

Agent section format:
<<<mycheck:sep(59)>>>
item1;100;OK
item2;75;WARNING
item3;25;CRITICAL
"""

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Service,
    Result,
    State,
    Metric,
    check_levels,
    render,
)


def parse_mycheck(string_table):
    """Parse agent section into dictionary keyed by item."""
    if not string_table:
        return None
    
    parsed = {}
    for line in string_table:
        if len(line) < 3:
            continue
        try:
            item_name = line[0]
            parsed[item_name] = {
                "value": float(line[1]),
                "status": line[2],
            }
        except (ValueError, IndexError):
            continue
    
    return parsed if parsed else None


def discover_mycheck(section):
    """Discover one service per item."""
    for item_name in section:
        yield Service(item=item_name)


def check_mycheck(item, params, section):
    """
    Check function with item and parameters.
    
    Args:
        item: The item name from discovery
        params: Parameters from ruleset (or defaults)
        section: Parsed section data
    """
    data = section.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary="Item not found in data")
        return
    
    value = data["value"]
    status = data["status"]
    
    # Use check_levels for threshold checking
    # Works with SimpleLevels from Rulesets API
    yield from check_levels(
        value,
        levels_upper=params.get("levels_upper"),
        levels_lower=params.get("levels_lower"),
        metric_name="mycheck_value",
        label="Value",
        render_func=render.percent,
        boundaries=(0.0, 100.0),
    )
    
    # Additional status information
    yield Result(
        state=State.OK,
        notice=f"Reported status: {status}",
    )


# Register agent section
agent_section_mycheck = AgentSection(
    name="mycheck",
    parse_function=parse_mycheck,
)

# Register check plugin with ruleset
check_plugin_mycheck = CheckPlugin(
    name="mycheck",
    service_name="My Check %s",  # %s = item placeholder
    discovery_function=discover_mycheck,
    check_function=check_mycheck,
    check_default_parameters={
        "levels_upper": ("fixed", (80.0, 90.0)),
        "levels_lower": ("fixed", (10.0, 5.0)),
    },
    check_ruleset_name="mycheck",  # Links to ruleset
)
