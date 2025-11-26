# SNMP-Based Check Plugin API Reference

## How SNMP Plugins Differ from Agent-Based

| Aspect | Agent-Based | SNMP-Based |
|--------|-------------|------------|
| Data source | Agent on host | SNMP queries from CheckMK server |
| Data selection | Agent decides | Plugin specifies exact OIDs |
| Discovery | Single phase | Two phases: detect → fetch |
| Performance | Agent pre-filters | Must minimize OID queries |

## Development Workflow

1. **Add device to monitoring** - Ensure basic SNMP works (SNMP Info, Uptime services)
2. **Create SNMP walk** - `cmk -v --snmpwalk mydevice`
3. **Analyze walk** - Find relevant OIDs in `~/var/check_mk/snmpwalks/mydevice`
4. **Translate OIDs** (optional) - `cmk --snmptranslate mydevice` (requires MIBs)
5. **Write plugin** - Define detect, fetch, parse, discover, check
6. **Test with simulation** - Use stored walk for development
7. **Deploy** - Test on real device

## Location

`~/local/lib/python3/cmk_addons/plugins/<family>/agent_based/`

## Complete Import Statement

```python
from cmk.agent_based.v2 import (
    CheckPlugin,
    SimpleSNMPSection,
    SNMPSection,
    SNMPTree,
    Service,
    Result,
    State,
    Metric,
    check_levels,
    render,
    StringTable,
    # Detection functions
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
```

## Finding OIDs

### Create SNMP Walk

```bash
# Full SNMP walk (can take minutes to hours!)
cmk -v --snmpwalk mydevice01

# Output location
cat ~/var/check_mk/snmpwalks/mydevice01
```

### Walk File Format

```
.1.3.6.1.2.1.1.1.0 Flintstones, Inc. Fred Router rev23
.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.424242.2.3
.1.3.6.1.2.1.1.3.0 546522419
.1.3.6.1.2.1.1.4.0 barney@example.com
.1.3.6.1.2.1.1.5.0 big-router-01
.1.3.6.1.2.1.1.6.0 Server room 23, Munich
```

### Translate with MIBs

```bash
# Translate OIDs to names (requires MIBs in ~/local/share/snmp/mibs/)
cmk --snmptranslate mydevice01 > /tmp/translated

# Output shows OID names:
# .1.3.6.1.2.1.1.4.0 barney@example.com --> SNMPv2-MIB::sysContact.0
```

## SimpleSNMPSection Class

For simple single-table SNMP queries:

```python
snmp_section_mydevice = SimpleSNMPSection(
    name="mydevice_section",
    parse_function=parse_mydevice,
    detect=startswith(".1.3.6.1.2.1.1.1.0", "MyDevice"),  # sysDescr
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.1",       # Base OID
        oids=[
            "1.0",  # sysDescr
            "4.0",  # sysContact
            "5.0",  # sysName
            "6.0",  # sysLocation
        ],
    ),
)
```

## SNMPSection Class

For complex queries with multiple OID tables:

```python
snmp_section_complex = SNMPSection(
    name="complex_section",
    parse_function=parse_complex,
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", "Cisco"),
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9."),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.2.2.1",  # ifTable
            oids=[
                "1",   # ifIndex
                "2",   # ifDescr
                "8",   # ifOperStatus
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.31.1.1.1",  # ifXTable
            oids=[
                "1",   # ifName
                "18",  # ifAlias
            ],
        ),
    ],
)
```

## SNMPTree Class

Defines which OIDs to fetch:

```python
SNMPTree(
    base=".1.3.6.1.2.1.1",    # Base OID (branch)
    oids=[
        "1.0",                 # Single leaf (ends with .0)
        "4.0",
        "5",                   # Branch - all leaves under it
    ],
)
```

**OID Types:**
- `.0` suffix = single scalar value (leaf)
- No `.0` suffix = table column (all rows)

## SNMP Detection Functions

### Detection Function Reference

| Function | Description | Negation |
|----------|-------------|----------|
| `startswith(oid, text)` | Value starts with text | `not_startswith` |
| `endswith(oid, text)` | Value ends with text | `not_endswith` |
| `contains(oid, text)` | Value contains text | `not_contains` |
| `equals(oid, text)` | Value equals text exactly | - |
| `matches(oid, regex)` | Value matches regex | `not_matches` |
| `exists(oid)` | OID exists (any value) | `not_exists` |

All text comparisons are **case-insensitive**.

### Basic Detection

```python
# Check sysDescr starts with text
detect=startswith(".1.3.6.1.2.1.1.1.0", "Cisco")

# Check sysObjectID contains value
detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.")

# Check exact match
detect=equals(".1.3.6.1.2.1.1.1.0", "ExactString")

# Regex match
detect=matches(".1.3.6.1.2.1.1.1.0", r"Cisco.*Switch.*")

# OID exists (any value)
detect=exists(".1.3.6.1.4.1.12345.1.0")
```

### Negated Detection

```python
detect=not_startswith(".1.3.6.1.2.1.1.1.0", "Linux")
detect=not_contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.")
detect=not_exists(".1.3.6.1.4.1.12345.1.0")
```

### Combined Detection

```python
# All conditions must match (AND)
detect=all_of(
    startswith(".1.3.6.1.2.1.1.1.0", "Cisco"),
    contains(".1.3.6.1.2.1.1.2.0", ".4.1.9."),
    exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.0"),
)

# Any condition matches (OR)
detect=any_of(
    startswith(".1.3.6.1.2.1.1.1.0", "Cisco IOS"),
    startswith(".1.3.6.1.2.1.1.1.0", "Cisco Nexus"),
    startswith(".1.3.6.1.2.1.1.1.0", "Cisco ASA"),
)

# Simplified with regex
detect=matches(".1.3.6.1.2.1.1.1.0", "Cisco (IOS|Nexus|ASA).*")

# Combined AND/OR
detect=all_of(
    any_of(
        startswith(".1.3.6.1.2.1.1.1.0", "Cisco"),
        startswith(".1.3.6.1.2.1.1.1.0", "Juniper"),
    ),
    exists(".1.3.6.1.2.1.47.1.1.1.1.0"),  # entPhysicalEntry
)
```

### Important Detection Guidelines

**Detection runs on EVERY SNMP device** - minimize OID queries!

```python
# GOOD: Check standard OID first (lazy evaluation stops at first failure)
detect=all_of(
    startswith(".1.3.6.1.2.1.1.1.0", "MyVendor"),  # sysDescr first
    exists(".1.3.6.1.4.1.12345.1.2.3.0"),          # Vendor OID second
)

# BAD: Vendor OID queried for ALL SNMP devices
detect=exists(".1.3.6.1.4.1.12345.1.0")
```

Priority order:
1. `sysDescr` (1.3.6.1.2.1.1.1.0) - always available
2. `sysObjectID` (1.3.6.1.2.1.1.2.0) - always available
3. Vendor-specific OIDs - only after filtering

## Parse Function for SNMP

### Scalar Values (leaves ending in .0)

```python
# fetch=SNMPTree(base=".1.3.6.1.2.1.1", oids=["4.0", "5.0", "6.0"])
# Results in: [['contact_value', 'name_value', 'location_value']]

def parse_mydevice(string_table):
    if not string_table or not string_table[0]:
        return None
    
    row = string_table[0]
    return {
        "contact": row[0],
        "name": row[1],
        "location": row[2],
    }
```

### Table Data (columns without .0)

```python
# fetch=SNMPTree(base=".1.3.6.1.2.1.2.2.1", oids=["1", "2", "8"])
# Results in: [['1', 'eth0', '1'], ['2', 'eth1', '2'], ...]

def parse_interfaces(string_table):
    parsed = {}
    for row in string_table:
        if len(row) < 3:
            continue
        idx, descr, status = row
        parsed[descr] = {
            "index": idx,
            "status": int(status),
        }
    return parsed
```

### Multiple Tables (SNMPSection with fetch list)

```python
def parse_complex(string_table):
    # string_table is list of tables in same order as fetch list
    if_table, ifx_table = string_table
    
    parsed = {}
    for if_row, ifx_row in zip(if_table, ifx_table):
        parsed[if_row[1]] = {  # ifDescr as key
            "index": if_row[0],
            "oper_status": if_row[2],
            "name": ifx_row[0],
            "alias": ifx_row[1],
        }
    return parsed
```

### Debug Parse Function

```python
def parse_mydevice(string_table):
    print(f"DEBUG: {string_table}")  # Visible in cmk -v output
    # ... rest of function
```

## Common OIDs Reference

### System MIB (1.3.6.1.2.1.1)

| OID | Name | Description |
|-----|------|-------------|
| .1.0 | sysDescr | System description |
| .2.0 | sysObjectID | Vendor OID |
| .3.0 | sysUpTime | Uptime (timeticks) |
| .4.0 | sysContact | Contact info |
| .5.0 | sysName | Hostname |
| .6.0 | sysLocation | Location |

### Interface MIB (1.3.6.1.2.1.2.2.1)

| OID | Name | Description |
|-----|------|-------------|
| .1 | ifIndex | Interface index |
| .2 | ifDescr | Description |
| .5 | ifSpeed | Speed (bps) |
| .7 | ifAdminStatus | Admin status |
| .8 | ifOperStatus | Oper status |

### Status Values

- ifOperStatus: 1=up, 2=down, 3=testing, 4=unknown, 5=dormant, 6=notPresent, 7=lowerLayerDown
- ifAdminStatus: 1=up, 2=down, 3=testing

## Complete SNMP Plugin Example

```python
#!/usr/bin/env python3
"""
Check plugin to verify device setup information.
Warns if contact, name, or location is missing.
"""

from cmk.agent_based.v2 import (
    CheckPlugin,
    SimpleSNMPSection,
    SNMPTree,
    Service,
    Result,
    State,
    startswith,
)


def parse_device_setup(string_table):
    """Parse SNMP data into dictionary."""
    if not string_table or not string_table[0]:
        return None
    
    row = string_table[0]
    return {
        "contact": row[0] if len(row) > 0 else "",
        "name": row[1] if len(row) > 1 else "",
        "location": row[2] if len(row) > 2 else "",
    }


def discover_device_setup(section):
    """Always discover one service."""
    if section:
        yield Service()


def check_device_setup(section):
    """Check that all setup fields are populated."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No SNMP data")
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


# SNMP Section - defines what data to fetch
snmp_section_device_setup = SimpleSNMPSection(
    name="device_setup",
    parse_function=parse_device_setup,
    detect=startswith(".1.3.6.1.2.1.1.1.0", "Flintstones"),  # Adapt to your device!
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.1",
        oids=["4.0", "5.0", "6.0"],  # contact, name, location
    ),
)


# Check Plugin - defines the service
check_plugin_device_setup = CheckPlugin(
    name="device_setup",
    service_name="Device Setup",
    discovery_function=discover_device_setup,
    check_function=check_device_setup,
)
```

## Testing SNMP Plugins

### Create and Use SNMP Walk

```bash
# Create SNMP walk (can take minutes!)
cmk -v --snmpwalk mydevice01

# View walk file
cat ~/var/check_mk/snmpwalks/mydevice01

# Translate OIDs (requires MIBs)
cmk --snmptranslate mydevice01 > /tmp/translated
```

### Use Stored Walk for Simulation

```bash
# Use stored walk instead of live SNMP
cmk --snmpwalk-cache mydevice01

# Or configure in GUI: Setup > Hosts > Properties
# SNMP > Simulate SNMP with stored walk
```

### Test Plugin

```bash
# Service discovery
cmk -vI --detect-plugins=device_setup mydevice01

# Execute check
cmk -v --detect-plugins=device_setup mydevice01

# Debug mode
cmk --debug --detect-plugins=device_setup mydevice01
```

## MIB Installation

Place MIB files in:
```
~/local/share/snmp/mibs/
```

MIBs enable OID translation and provide documentation, but are **not required** for plugin operation.

## Troubleshooting

### Plugin Not Detecting Device

1. **Check sysDescr matches**:
   ```bash
   grep "1.3.6.1.2.1.1.1.0" ~/var/check_mk/snmpwalks/mydevice01
   ```

2. **Test detection manually**:
   ```bash
   cmk -v --snmpget mydevice01 .1.3.6.1.2.1.1.1.0
   ```

3. **Check case sensitivity**: Detection functions are case-insensitive

### No Data Returned

1. **Verify OIDs exist in walk**:
   ```bash
   grep "1.3.6.1.2.1.1.4" ~/var/check_mk/snmpwalks/mydevice01
   ```

2. **Check OID format**: Use `.0` for scalars, omit for tables

3. **Debug parse function**: Add `print()` statements

### SNMP Timeout

- Device may be slow - increase timeout in host settings
- Full walk takes long time - be patient
- Check network connectivity and SNMP credentials

### Common Mistakes

| Mistake | Solution |
|---------|----------|
| Wrong OID format | Use `.0` for single values |
| Vendor OID in detect without filter | Always filter by sysDescr first |
| Forgetting to import detection function | Add to import statement |
| Case-sensitive string comparison | Detection is case-insensitive |
| Wrong string_table structure | Debug with `print()` |

## Files and Directories

| Path | Description |
|------|-------------|
| `~/local/lib/python3/cmk_addons/plugins/<family>/agent_based/` | Plugin files |
| `~/var/check_mk/snmpwalks/` | Stored SNMP walks |
| `~/local/share/snmp/mibs/` | Custom MIB files |
