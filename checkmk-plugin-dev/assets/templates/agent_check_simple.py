#!/usr/bin/env python3
"""
Simple Agent-Based Check Plugin Template
========================================
Location: ~/local/lib/python3/cmk_addons/plugins/<family>/agent_based/

Agent section format:
<<<mycheck>>>
value1
value2
"""

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Service,
    Result,
    State,
)


def parse_mycheck(string_table):
    """Parse agent section data."""
    if not string_table:
        return None
    
    # Simple: just extract first value
    return {"value": string_table[0][0] if string_table[0] else None}


def discover_mycheck(section):
    """Discover service (single service, no item)."""
    if section:
        yield Service()


def check_mycheck(section):
    """Check function."""
    if not section or not section.get("value"):
        yield Result(state=State.UNKNOWN, summary="No data")
        return
    
    value = section["value"]
    yield Result(state=State.OK, summary=f"Value: {value}")


# Register agent section
agent_section_mycheck = AgentSection(
    name="mycheck",
    parse_function=parse_mycheck,
)

# Register check plugin
check_plugin_mycheck = CheckPlugin(
    name="mycheck",
    service_name="My Check",
    discovery_function=discover_mycheck,
    check_function=check_mycheck,
)
