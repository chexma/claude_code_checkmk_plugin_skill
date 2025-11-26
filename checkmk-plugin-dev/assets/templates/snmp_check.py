#!/usr/bin/env python3
"""
SNMP-Based Check Plugin Template (Enhanced)
============================================
Location: ~/local/lib/python3/cmk_addons/plugins/<family>/agent_based/

This template includes multiple SNMP check examples:
1. Simple scalar check (single values like sysContact)
2. Table-based check (interface status)
3. Check with metrics and thresholds
4. Check with rate calculation (counters)

SNMP Plugin Development Workflow:
1. Add device to monitoring, verify SNMP works
2. Create SNMP walk: cmk -v --snmpwalk mydevice
3. Analyze walk: cat ~/var/check_mk/snmpwalks/mydevice
4. Translate OIDs (optional): cmk --snmptranslate mydevice
5. Write plugin with detect, fetch, parse, discover, check
6. Test: cmk -vI --detect-plugins=myplugin mydevice
7. Deploy and activate changes
"""

import time
from typing import Any, Mapping, Optional
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    SimpleSNMPSection,
    SNMPTree,
    Service,
    Result,
    State,
    Metric,
    render,
    check_levels,
    GetRateError,
    get_value_store,
    get_rate,
    # Detection functions - all case-insensitive
    startswith,
    endswith,
    contains,
    matches,
    exists,
    equals,
    # Negations
    not_startswith,
    not_endswith,
    not_contains,
    not_matches,
    not_exists,
    # Combinators
    all_of,
    any_of,
)


# =============================================================================
# EXAMPLE 1: Simple Scalar Check (Device Setup Information)
# =============================================================================
# Checks if sysContact, sysName, sysLocation are configured

def parse_device_setup(string_table) -> Optional[dict]:
    """
    Parse scalar SNMP values.
    
    For OIDs ending in .0 (scalar), string_table structure is:
    [[value1, value2, value3]]  - single row with all values
    """
    if not string_table or not string_table[0]:
        return None
    
    row = string_table[0]
    return {
        "contact": row[0] if len(row) > 0 else "",
        "name": row[1] if len(row) > 1 else "",
        "location": row[2] if len(row) > 2 else "",
    }


def discover_device_setup(section) -> DiscoveryResult:
    """Discover single service (no item)."""
    if section:
        yield Service()


def check_device_setup(section) -> CheckResult:
    """Check that all setup fields are populated."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No SNMP data received")
        return
    
    missing = []
    for field in ["contact", "name", "location"]:
        if not section.get(field):
            missing.append(field)
    
    if missing:
        yield Result(
            state=State.WARN,
            summary=f"Missing: {', '.join(missing)}"
        )
    else:
        yield Result(
            state=State.OK,
            summary=f"Name: {section['name']}, Location: {section['location']}"
        )


snmp_section_device_setup = SimpleSNMPSection(
    name="device_setup",
    parse_function=parse_device_setup,
    # IMPORTANT: Adapt this to match YOUR device's sysDescr!
    detect=startswith(".1.3.6.1.2.1.1.1.0", "MyDevice"),
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.1",
        oids=[
            "4.0",  # sysContact
            "5.0",  # sysName
            "6.0",  # sysLocation
        ],
    ),
)

check_plugin_device_setup = CheckPlugin(
    name="device_setup",
    service_name="Device Setup",
    discovery_function=discover_device_setup,
    check_function=check_device_setup,
)


# =============================================================================
# EXAMPLE 2: Table-Based Check (Interface Status)
# =============================================================================
# Monitors interface operational status

def parse_interface_status(string_table) -> Optional[dict]:
    """
    Parse SNMP table data.
    
    For table OIDs (no .0 suffix), string_table structure is:
    [[row1_col1, row1_col2, ...], [row2_col1, row2_col2, ...], ...]
    
    Each row is one table entry (e.g., one interface).
    """
    if not string_table:
        return None
    
    parsed = {}
    for row in string_table:
        if len(row) < 4:
            continue
        
        idx, descr, admin_status, oper_status = row[:4]
        
        # Skip empty descriptions
        if not descr:
            continue
        
        parsed[descr] = {
            "index": idx,
            "admin_status": int(admin_status) if admin_status.isdigit() else 0,
            "oper_status": int(oper_status) if oper_status.isdigit() else 0,
        }
    
    return parsed if parsed else None


def discover_interface_status(section) -> DiscoveryResult:
    """Discover one service per interface."""
    for interface_name, data in section.items():
        # Only discover administratively enabled interfaces
        if data.get("admin_status") == 1:
            yield Service(item=interface_name)


def check_interface_status(item: str, section) -> CheckResult:
    """Check interface operational status."""
    data = section.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary="Interface not found")
        return
    
    oper_status = data["oper_status"]
    admin_status = data["admin_status"]
    
    # ifOperStatus values
    oper_status_map = {
        1: (State.OK, "up"),
        2: (State.CRIT, "down"),
        3: (State.WARN, "testing"),
        4: (State.UNKNOWN, "unknown"),
        5: (State.WARN, "dormant"),
        6: (State.CRIT, "notPresent"),
        7: (State.CRIT, "lowerLayerDown"),
    }
    
    state, status_text = oper_status_map.get(oper_status, (State.UNKNOWN, "invalid"))
    
    # If admin down, don't alert on oper down
    if admin_status != 1:
        state = State.OK
        status_text = f"{status_text} (admin down)"
    
    yield Result(
        state=state,
        summary=f"Operational status: {status_text}",
    )


snmp_section_interface_status = SimpleSNMPSection(
    name="interface_status",
    parse_function=parse_interface_status,
    detect=startswith(".1.3.6.1.2.1.1.1.0", "MyDevice"),
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.2.2.1",  # ifTable
        oids=[
            "1",   # ifIndex
            "2",   # ifDescr
            "7",   # ifAdminStatus (1=up, 2=down, 3=testing)
            "8",   # ifOperStatus
        ],
    ),
)

check_plugin_interface_status = CheckPlugin(
    name="interface_status",
    sections=["interface_status"],
    service_name="Interface %s",
    discovery_function=discover_interface_status,
    check_function=check_interface_status,
)


# =============================================================================
# EXAMPLE 3: Check with Metrics and Thresholds (CPU/Memory)
# =============================================================================
# Demonstrates metrics, thresholds, and check_levels()

def parse_system_resources(string_table) -> Optional[dict]:
    """Parse CPU and memory values."""
    if not string_table or not string_table[0]:
        return None
    
    row = string_table[0]
    
    try:
        return {
            "cpu_percent": float(row[0]) if row[0] else 0.0,
            "memory_used": int(row[1]) if len(row) > 1 and row[1] else 0,
            "memory_total": int(row[2]) if len(row) > 2 and row[2] else 0,
        }
    except (ValueError, IndexError):
        return None


def discover_system_resources(section) -> DiscoveryResult:
    """Discover if data is available."""
    if section and section.get("memory_total", 0) > 0:
        yield Service()


def check_system_resources(
    params: Mapping[str, Any],
    section,
) -> CheckResult:
    """Check CPU and memory with configurable thresholds."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data")
        return
    
    # CPU check with thresholds
    cpu_percent = section["cpu_percent"]
    yield from check_levels(
        cpu_percent,
        metric_name="cpu_percent",
        levels_upper=params.get("cpu_levels"),  # (warn, crit) tuple
        render_func=render.percent,
        label="CPU",
    )
    
    # Memory check
    mem_used = section["memory_used"]
    mem_total = section["memory_total"]
    
    if mem_total > 0:
        mem_percent = (mem_used / mem_total) * 100
        
        yield from check_levels(
            mem_percent,
            metric_name="memory_percent",
            levels_upper=params.get("memory_levels"),
            render_func=render.percent,
            label="Memory",
        )
        
        # Additional metric: absolute memory used
        yield Metric(
            "memory_used",
            mem_used,
            boundaries=(0, mem_total),
        )


snmp_section_system_resources = SimpleSNMPSection(
    name="system_resources",
    parse_function=parse_system_resources,
    detect=startswith(".1.3.6.1.2.1.1.1.0", "MyDevice"),
    # Example vendor-specific OIDs (adapt to your device!)
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12345.1",  # Vendor enterprise OID
        oids=[
            "1.0",  # CPU percent
            "2.0",  # Memory used (bytes)
            "3.0",  # Memory total (bytes)
        ],
    ),
)

check_plugin_system_resources = CheckPlugin(
    name="system_resources",
    sections=["system_resources"],
    service_name="System Resources",
    discovery_function=discover_system_resources,
    check_function=check_system_resources,
    # Default parameters (can be overridden by ruleset)
    check_default_parameters={
        "cpu_levels": (80.0, 90.0),      # warn at 80%, crit at 90%
        "memory_levels": (70.0, 85.0),   # warn at 70%, crit at 85%
    },
)


# =============================================================================
# EXAMPLE 4: Rate Calculation (Interface Traffic)
# =============================================================================
# Demonstrates counter handling and rate calculation

def parse_interface_traffic(string_table) -> Optional[dict]:
    """Parse interface traffic counters."""
    if not string_table:
        return None
    
    parsed = {}
    for row in string_table:
        if len(row) < 4:
            continue
        
        idx, descr, in_octets, out_octets = row[:4]
        
        if not descr:
            continue
        
        try:
            parsed[descr] = {
                "index": idx,
                "in_octets": int(in_octets) if in_octets else 0,
                "out_octets": int(out_octets) if out_octets else 0,
            }
        except ValueError:
            continue
    
    return parsed if parsed else None


def discover_interface_traffic(section) -> DiscoveryResult:
    """Discover interfaces with traffic counters."""
    for interface_name in section:
        yield Service(item=interface_name)


def check_interface_traffic(item: str, section) -> CheckResult:
    """Check interface traffic rates."""
    data = section.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary="Interface not found")
        return
    
    value_store = get_value_store()
    now = time.time()
    
    try:
        # Calculate bytes/sec from counter
        in_rate = get_rate(
            value_store,
            f"in_octets.{item}",
            now,
            data["in_octets"],
        )
        out_rate = get_rate(
            value_store,
            f"out_octets.{item}",
            now,
            data["out_octets"],
        )
    except GetRateError:
        yield Result(state=State.OK, summary="Collecting data...")
        return
    
    # Convert to bits/sec for display
    in_bps = in_rate * 8
    out_bps = out_rate * 8
    
    yield Result(
        state=State.OK,
        summary=f"In: {render.networkbandwidth(in_bps)}, Out: {render.networkbandwidth(out_bps)}"
    )
    
    yield Metric("if_in_bps", in_bps)
    yield Metric("if_out_bps", out_bps)


snmp_section_interface_traffic = SimpleSNMPSection(
    name="interface_traffic",
    parse_function=parse_interface_traffic,
    detect=startswith(".1.3.6.1.2.1.1.1.0", "MyDevice"),
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.2.2.1",  # ifTable
        oids=[
            "1",    # ifIndex
            "2",    # ifDescr
            "10",   # ifInOctets (32-bit counter)
            "16",   # ifOutOctets (32-bit counter)
            # For high-speed interfaces, use ifXTable:
            # base=".1.3.6.1.2.1.31.1.1.1"
            # "6",  # ifHCInOctets (64-bit)
            # "10", # ifHCOutOctets (64-bit)
        ],
    ),
)

check_plugin_interface_traffic = CheckPlugin(
    name="interface_traffic",
    sections=["interface_traffic"],
    service_name="Traffic %s",
    discovery_function=discover_interface_traffic,
    check_function=check_interface_traffic,
)


# =============================================================================
# EXAMPLE 5: Detection Patterns Reference
# =============================================================================
# Various detection examples for different scenarios

# Simple: Match by sysDescr prefix
detect_by_sysdescr = startswith(".1.3.6.1.2.1.1.1.0", "Cisco IOS")

# Match multiple device types (OR)
detect_multiple_types = any_of(
    startswith(".1.3.6.1.2.1.1.1.0", "Cisco IOS"),
    startswith(".1.3.6.1.2.1.1.1.0", "Cisco NX-OS"),
    startswith(".1.3.6.1.2.1.1.1.0", "Cisco ASA"),
)

# Same with regex (more efficient)
detect_with_regex = matches(".1.3.6.1.2.1.1.1.0", r"Cisco (IOS|NX-OS|ASA).*")

# Combine standard + vendor OID (AND with lazy evaluation)
detect_vendor_specific = all_of(
    # Check standard OID first - stops here if no match
    startswith(".1.3.6.1.2.1.1.1.0", "MyVendor"),
    # Only checked if sysDescr matches
    exists(".1.3.6.1.4.1.12345.1.0"),
)

# Complex: Multiple conditions
detect_complex = all_of(
    # Must be one of these vendors
    any_of(
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9."),    # Cisco
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2636."), # Juniper
    ),
    # Must have entity MIB
    exists(".1.3.6.1.2.1.47.1.1.1.1.1"),
    # Must NOT be a specific model
    not_contains(".1.3.6.1.2.1.1.1.0", "legacy"),
)


# =============================================================================
# TESTING COMMANDS
# =============================================================================
"""
# Create SNMP walk (may take minutes!)
cmk -v --snmpwalk mydevice

# View walk file
cat ~/var/check_mk/snmpwalks/mydevice

# Translate OIDs (requires MIBs)
cmk --snmptranslate mydevice > /tmp/translated

# Test with simulation (uses stored walk)
# Configure in GUI: Setup > Hosts > mydevice > SNMP > Simulate with stored walk

# Service discovery
cmk -vI --detect-plugins=device_setup mydevice

# Check execution
cmk -v --detect-plugins=device_setup mydevice

# Debug mode
cmk --debug --detect-plugins=device_setup mydevice

# Full agent output
cmk -d mydevice
"""
