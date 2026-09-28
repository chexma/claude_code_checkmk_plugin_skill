#!/usr/bin/env python3
"""
Multi-Table SNMP Check Plugin Template
======================================
Location: ~/local/lib/python3/cmk_addons/plugins/<family>/agent_based/

This template demonstrates how to:
1. Fetch data from multiple SNMP tables
2. Correlate data across tables (e.g., ifTable + ifXTable)
3. Handle complex data structures
4. Create comprehensive interface monitoring

Use SNMPSection (not SimpleSNMPSection) when you need multiple OID trees.
"""

import time
from typing import Any, Mapping, Optional, NamedTuple
from dataclasses import dataclass
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    SNMPSection,  # Note: SNMPSection, not SimpleSNMPSection
    SNMPTree,
    OIDEnd,
    Service,
    Result,
    State,
    Metric,
    render,
    check_levels,
    GetRateError,
    get_value_store,
    get_rate,
    startswith,
    contains,
    all_of,
    any_of,
)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class InterfaceData:
    """Structured interface data from multiple SNMP tables."""
    index: str
    descr: str
    name: str
    alias: str
    if_type: int
    speed: int
    admin_status: int
    oper_status: int
    in_octets: int
    out_octets: int
    in_errors: int
    out_errors: int
    
    @property
    def is_up(self) -> bool:
        return self.oper_status == 1
    
    @property
    def is_admin_up(self) -> bool:
        return self.admin_status == 1
    
    @property
    def display_name(self) -> str:
        """Best name for display."""
        return self.name or self.alias or self.descr


# Type alias for parsed section
Section = Mapping[str, InterfaceData]


# =============================================================================
# PARSE FUNCTION FOR MULTIPLE TABLES
# =============================================================================

def parse_multi_table_interfaces(string_table) -> Optional[Section]:
    """
    Parse data from multiple SNMP tables.
    
    When using SNMPSection with multiple SNMPTree entries,
    string_table is a list of tables in the same order as fetch list:
    
    string_table = [
        table1_data,  # First SNMPTree
        table2_data,  # Second SNMPTree
        ...
    ]
    
    Each table_data is a list of rows:
    [[row1_col1, row1_col2, ...], [row2_col1, ...], ...]
    """
    if not string_table or len(string_table) < 3:
        return None
    
    # Unpack tables in order they were defined in fetch list
    if_table = string_table[0]      # ifTable basic info
    ifx_table = string_table[1]     # ifXTable extended info
    if_counters = string_table[2]   # Counter table
    
    # Build lookup dict by ifIndex for correlation
    ifx_by_index = {}
    for row in ifx_table:
        if len(row) >= 3:
            idx, name, alias = row[0], row[1], row[2]
            ifx_by_index[idx] = {"name": name, "alias": alias}
    
    counters_by_index = {}
    for row in if_counters:
        if len(row) >= 5:
            idx = row[0]
            counters_by_index[idx] = {
                "in_octets": int(row[1]) if row[1] else 0,
                "out_octets": int(row[2]) if row[2] else 0,
                "in_errors": int(row[3]) if row[3] else 0,
                "out_errors": int(row[4]) if row[4] else 0,
            }
    
    # Merge data from all tables
    parsed: dict[str, InterfaceData] = {}
    
    for row in if_table:
        if len(row) < 6:
            continue
        
        idx, descr, if_type, speed, admin_status, oper_status = row[:6]
        
        if not descr:
            continue
        
        # Get extended info (may not exist)
        ifx_data = ifx_by_index.get(idx, {})
        counter_data = counters_by_index.get(idx, {})
        
        interface = InterfaceData(
            index=idx,
            descr=descr,
            name=ifx_data.get("name", ""),
            alias=ifx_data.get("alias", ""),
            if_type=int(if_type) if if_type.isdigit() else 0,
            speed=int(speed) if speed.isdigit() else 0,
            admin_status=int(admin_status) if admin_status.isdigit() else 0,
            oper_status=int(oper_status) if oper_status.isdigit() else 0,
            in_octets=counter_data.get("in_octets", 0),
            out_octets=counter_data.get("out_octets", 0),
            in_errors=counter_data.get("in_errors", 0),
            out_errors=counter_data.get("out_errors", 0),
        )
        
        # Use display_name as key
        parsed[interface.display_name] = interface
    
    return parsed if parsed else None


# =============================================================================
# DISCOVERY FUNCTION
# =============================================================================

def discover_multi_table_interfaces(section: Section) -> DiscoveryResult:
    """
    Discover interfaces.
    
    Can add parameters for discovered services using Service(parameters=...).
    """
    for name, interface in section.items():
        # Only discover physical interfaces (skip loopback, etc.)
        # ifType: 6=ethernetCsmacd, 117=gigabitEthernet, 24=softwareLoopback
        if interface.if_type in (6, 117, 62, 69, 135, 136):
            # Can save discovery-time state
            yield Service(
                item=name,
                parameters={
                    "discovered_speed": interface.speed,
                    "discovered_oper_status": interface.oper_status,
                },
            )


# =============================================================================
# CHECK FUNCTION
# =============================================================================

def check_multi_table_interfaces(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """
    Check interface with comprehensive metrics.
    
    Features:
    - Status monitoring
    - Traffic rate calculation
    - Error rate monitoring
    - Speed change detection
    """
    interface = section.get(item)
    if not interface:
        yield Result(state=State.UNKNOWN, summary="Interface not found")
        return
    
    # -------------------------------------------------------------------------
    # Status Check
    # -------------------------------------------------------------------------
    oper_status_map = {
        1: (State.OK, "up"),
        2: (State.CRIT, "down"),
        3: (State.WARN, "testing"),
        4: (State.UNKNOWN, "unknown"),
        5: (State.WARN, "dormant"),
        6: (State.CRIT, "notPresent"),
        7: (State.CRIT, "lowerLayerDown"),
    }
    
    state, status_text = oper_status_map.get(
        interface.oper_status,
        (State.UNKNOWN, "invalid")
    )
    
    # Expected status from discovery or params
    expected_status = params.get("expected_status", 1)
    if interface.oper_status != expected_status and interface.is_admin_up:
        state = State.CRIT
        status_text = f"{status_text} (expected: up)"
    elif not interface.is_admin_up:
        state = State.OK
        status_text = f"{status_text} (admin down)"
    
    yield Result(
        state=state,
        summary=f"Status: {status_text}",
    )
    
    # -------------------------------------------------------------------------
    # Speed Check
    # -------------------------------------------------------------------------
    if interface.speed > 0:
        # ifSpeed is bits/s; render.nicspeed() expects bytes/s
        speed_text = render.nicspeed(interface.speed / 8)
        
        # Check for speed change since discovery
        discovered_speed = params.get("discovered_speed", 0)
        if discovered_speed and interface.speed != discovered_speed:
            yield Result(
                state=State.WARN,
                summary=f"Speed changed: {speed_text} (was {render.nicspeed(discovered_speed / 8)})"
            )
        else:
            yield Result(state=State.OK, notice=f"Speed: {speed_text}")
    
    # -------------------------------------------------------------------------
    # Traffic Rates
    # -------------------------------------------------------------------------
    value_store = get_value_store()
    now = time.time()
    
    # Compute ALL rates before giving up: a GetRateError on the first counter
    # must not prevent the other counters from being initialized.
    counters = {
        "in_octets": interface.in_octets,
        "out_octets": interface.out_octets,
        "in_errors": interface.in_errors,
        "out_errors": interface.out_errors,
    }
    rates = {}
    for key, counter in counters.items():
        try:
            rates[key] = get_rate(value_store, f"{key}.{item}", now, counter)
        except GetRateError:
            pass
    
    if "in_octets" in rates and "out_octets" in rates:
        in_rate, out_rate = rates["in_octets"], rates["out_octets"]
        
        # render.networkbandwidth() expects BYTES/s (multiplies by 8 itself)
        yield Result(
            state=State.OK,
            summary=f"In: {render.networkbandwidth(in_rate)}, Out: {render.networkbandwidth(out_rate)}"
        )
        
        # Metrics and utilization in bits/s (same unit as ifSpeed)
        in_bps = in_rate * 8
        out_bps = out_rate * 8
        
        yield Metric("if_in_bps", in_bps)
        yield Metric("if_out_bps", out_bps)
        
        # Utilization if speed known
        if interface.speed > 0:
            in_util = (in_bps / interface.speed) * 100
            out_util = (out_bps / interface.speed) * 100
            
            # Check utilization thresholds
            util_levels = params.get("utilization_levels", ("fixed", (80.0, 90.0)))
            
            yield from check_levels(
                max(in_util, out_util),
                metric_name="if_util_percent",
                levels_upper=util_levels,
                render_func=render.percent,
                label="Utilization",
            )
    else:
        yield Result(state=State.OK, notice="Traffic: collecting data...")
    
    # -------------------------------------------------------------------------
    # Error Rates
    # -------------------------------------------------------------------------
    if "in_errors" in rates and "out_errors" in rates:
        total_err_rate = rates["in_errors"] + rates["out_errors"]
        
        if total_err_rate > 0:
            error_levels = params.get("error_levels", ("fixed", (1.0, 10.0)))  # errors/sec
            
            yield from check_levels(
                total_err_rate,
                metric_name="if_errors_rate",
                levels_upper=error_levels,
                render_func=lambda x: f"{x:.2f}/s",
                label="Errors",
            )


# =============================================================================
# SNMP SECTION WITH MULTIPLE TABLES
# =============================================================================

snmp_section_multi_table_interfaces = SNMPSection(
    name="multi_table_interfaces",
    parse_function=parse_multi_table_interfaces,
    
    # Detection criteria
    # Adapt to your device! (all_of()/any_of() need at least TWO specs)
    detect=startswith(".1.3.6.1.2.1.1.1.0", "MyDevice"),
    # Or use a more generic detection:
    # detect=any_of(
    #     contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9."),    # Cisco
    #     contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2636."), # Juniper
    # ),
    
    # Fetch from multiple tables - ORDER MATTERS!
    # Parse function receives tables in this exact order
    fetch=[
        # Table 1: ifTable basic info
        SNMPTree(
            base=".1.3.6.1.2.1.2.2.1",
            oids=[
                "1",   # ifIndex
                "2",   # ifDescr
                "3",   # ifType
                "5",   # ifSpeed
                "7",   # ifAdminStatus
                "8",   # ifOperStatus
            ],
        ),
        # Table 2: ifXTable extended info
        SNMPTree(
            base=".1.3.6.1.2.1.31.1.1.1",
            oids=[
                OIDEnd(),  # ifIndex (ifXTable has no index column - use the OID suffix)
                "1",       # ifName
                "18",      # ifAlias
            ],
        ),
        # Table 3: Counters (could also use 64-bit counters from ifXTable)
        SNMPTree(
            base=".1.3.6.1.2.1.2.2.1",
            oids=[
                "1",   # ifIndex (for correlation)
                "10",  # ifInOctets
                "16",  # ifOutOctets
                "14",  # ifInErrors
                "20",  # ifOutErrors
            ],
        ),
    ],
)


# =============================================================================
# CHECK PLUGIN
# =============================================================================

check_plugin_multi_table_interfaces = CheckPlugin(
    name="multi_table_interfaces",
    sections=["multi_table_interfaces"],
    service_name="Interface %s",
    discovery_function=discover_multi_table_interfaces,
    check_function=check_multi_table_interfaces,
    check_default_parameters={
        "expected_status": 1,  # up
        # check_levels() format - plain (warn, crit) tuples raise TypeError!
        "utilization_levels": ("fixed", (80.0, 90.0)),
        "error_levels": ("fixed", (1.0, 10.0)),
    },
    # If you create a ruleset, reference it here:
    # check_ruleset_name="multi_table_interfaces",
)


# =============================================================================
# ALTERNATIVE: HIGH-SPEED INTERFACES (64-bit counters)
# =============================================================================
"""
For interfaces faster than 100 Mbps, use 64-bit counters from ifXTable
to avoid counter wraparound:

SNMPTree(
    base=".1.3.6.1.2.1.31.1.1.1",
    oids=[
        "1",   # ifName
        "6",   # ifHCInOctets (64-bit)
        "10",  # ifHCOutOctets (64-bit)
        "15",  # ifHighSpeed (Mbps, not bps!)
    ],
),

Note: ifHighSpeed is in Mbps, multiply by 1,000,000 for bps.
"""


# =============================================================================
# ALTERNATIVE: VENDOR-SPECIFIC TABLES
# =============================================================================
"""
Many vendors provide additional tables with more detail.
Example: Cisco CPU/Memory via vendor OIDs

snmp_section_vendor = SNMPSection(
    name="vendor_health",
    parse_function=parse_vendor_health,
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9."),  # Cisco
    fetch=[
        # Cisco CPU
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.109.1.1.1.1",
            oids=[
                "2",   # cpmCPUTotalPhysicalIndex
                "6",   # cpmCPUTotal5min
            ],
        ),
        # Cisco Memory
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.48.1.1.1",
            oids=[
                "2",   # ciscoMemoryPoolName
                "5",   # ciscoMemoryPoolUsed
                "6",   # ciscoMemoryPoolFree
            ],
        ),
    ],
)
"""


# =============================================================================
# TESTING COMMANDS
# =============================================================================
"""
# Create SNMP walk
cmk -v --snmpwalk mydevice

# Check what's in the walk for ifTable
grep "1.3.6.1.2.1.2.2.1" ~/var/check_mk/snmpwalks/mydevice

# Check ifXTable
grep "1.3.6.1.2.1.31.1.1.1" ~/var/check_mk/snmpwalks/mydevice

# Test with simulation (stored walk)
cmk -v --usewalk --detect-plugins=multi_table_interfaces mydevice

# Discovery
cmk -vI --detect-plugins=multi_table_interfaces mydevice

# Check
cmk -v --detect-plugins=multi_table_interfaces mydevice

# Debug
cmk --debug --detect-plugins=multi_table_interfaces mydevice
"""
