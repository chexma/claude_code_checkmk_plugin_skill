# Agent-Based Check API V2 Reference

## Location
`~/local/lib/python3/cmk_addons/plugins/<family>/agent_based/`

## Complete Import Statement
```python
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    InventoryPlugin,
    Service,
    Result,
    State,
    Metric,
    check_levels,
    render,
    StringTable,
    RuleSetType,
    HostLabel,
    get_value_store,
)
```

## AgentSection Class

Creates a section from agent output marked by `<<<section_name>>>`.

```python
agent_section_mycheck = AgentSection(
    name="mycheck",                    # Must match <<<mycheck>>> header
    parse_function=parse_mycheck,      # Required: transforms string_table
    parsed_section_name=None,          # Optional: override section name
    host_label_function=None,          # Optional: for auto host labels
    supersedes=None,                   # Optional: list of sections to replace
)
```

### Parse Function Pattern
```python
def parse_mycheck(string_table: StringTable) -> dict | None:
    """
    string_table is List[List[str]] - lines split by separator
    Return None if section is empty/invalid (plugin won't run)
    """
    if not string_table:
        return None
    
    parsed = {}
    for line in string_table:
        # Process each line
        key = line[0]
        parsed[key] = {
            "value1": line[1],
            "value2": int(line[2]) if len(line) > 2 else 0,
        }
    return parsed
```

## CheckPlugin Class

```python
check_plugin_mycheck = CheckPlugin(
    name="mycheck",                           # Unique plugin name
    sections=["mycheck"],                     # List of sections to use
    service_name="My Service %s",             # %s for item placeholder
    discovery_function=discover_mycheck,
    check_function=check_mycheck,
    discovery_default_parameters=None,
    discovery_ruleset_name=None,
    check_default_parameters={},              # Required if using ruleset
    check_ruleset_name="mycheck",             # Links to ruleset
    cluster_check_function=None,
)
```

### Discovery Function Patterns

**Without items (single service):**
```python
def discover_mycheck(section):
    if section:  # Only discover if data exists
        yield Service()
```

**With items (multiple services):**
```python
def discover_mycheck(section):
    for item_name in section:
        yield Service(item=item_name)
```

**With discovery parameters:**
```python
def discover_mycheck(params, section):
    for item_name, data in section.items():
        if data["value"] > params.get("min_value", 0):
            yield Service(
                item=item_name,
                parameters={"discovered_value": data["value"]}
            )
```

### Check Function Patterns

**Without item:**
```python
def check_mycheck(section):
    yield Result(state=State.OK, summary="Status OK")
```

**With item:**
```python
def check_mycheck(item, section):
    data = section.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary="Item not found")
        return
    yield Result(state=State.OK, summary=f"Value: {data['value']}")
```

**With parameters:**
```python
def check_mycheck(item, params, section):
    data = section.get(item)
    if not data:
        return  # Let CheckMK handle missing item
    
    warn, crit = params.get("levels", (80, 90))
    value = data["value"]
    
    if value >= crit:
        state = State.CRIT
    elif value >= warn:
        state = State.WARN
    else:
        state = State.OK
    
    yield Result(state=state, summary=f"Value: {value}")
    yield Metric("mymetric", value, levels=(warn, crit))
```

## check_levels() Function

Best practice for threshold checking - integrates with Rulesets API.

```python
yield from check_levels(
    value,                              # The value to check
    levels_upper=("fixed", (80.0, 90.0)),  # Upper thresholds (warn, crit)
    levels_lower=("fixed", (10.0, 5.0)),   # Lower thresholds (warn, crit)
    metric_name="mymetric",             # Name for performance data
    label="CPU Usage",                  # Label in output
    render_func=render.percent,         # How to display value
    boundaries=(0.0, 100.0),            # Min/max for graphs
    notice_only=False,                  # True: show in summary only if not OK
)
```

### Levels Format (from Rulesets API)
```python
# Fixed levels
levels_upper=("fixed", (80.0, 90.0))

# No levels
levels_upper=None

# From params dictionary
levels_upper=params.get("cpu_levels")
```

## Metric Class

Direct metric creation (when not using check_levels):

```python
yield Metric(
    name="my_metric",
    value=42.5,
    levels=(80.0, 90.0),        # Optional: warn, crit thresholds
    boundaries=(0.0, 100.0),    # Optional: min, max
)
```

## Result Class

```python
yield Result(
    state=State.OK,              # OK, WARN, CRIT, UNKNOWN
    summary="Short text",        # Always shown (keep under 60 chars)
    details="Extended info",     # Only in service details
)

# notice parameter: only shows in summary if state != OK
yield Result(
    state=State.OK,
    notice="Hidden when OK, visible otherwise",
)
```

## render Module Functions

| Function | Input | Output Example |
|----------|-------|----------------|
| `render.percent(50.5)` | Percentage | "50.50%" |
| `render.bytes(1024)` | Bytes | "1.00 KiB" |
| `render.disksize(1000000)` | Bytes (base 1000) | "1.00 MB" |
| `render.filesize(12345678)` | Bytes (exact) | "12,345,678 B" |
| `render.networkbandwidth(125000)` | Bytes/s | "1.00 MBit/s" |
| `render.iobandwidth(1000000)` | Bytes/s | "1.00 MB/s" |
| `render.nicspeed(125000000)` | Bytes/s | "1 GBit/s" |
| `render.timespan(3661)` | Seconds | "1 hour 1 minute" |
| `render.datetime(timestamp)` | Unix time | "Jan 01 2024, 12:00" |
| `render.date(timestamp)` | Unix time | "Jan 01 2024" |
| `render.frequency(1000000000)` | Hz | "1.00 GHz" |

## Value Store (Persistent Data)

For rate calculations or remembering values between checks:

```python
from cmk.agent_based.v2 import get_value_store, GetRateError

def check_mycheck(item, section):
    value_store = get_value_store()
    
    # Store a value
    value_store["last_value"] = current_value
    
    # Calculate rate
    try:
        rate = get_rate(
            value_store,
            "counter_key",
            time.time(),
            counter_value,
            raise_overflow=True,
        )
    except GetRateError:
        yield Result(state=State.OK, summary="Awaiting data")
        return
```

## Host Labels

Auto-assign labels during discovery:

```python
def host_label_mycheck(section):
    if section.get("os") == "linux":
        yield HostLabel("os", "linux")

agent_section_mycheck = AgentSection(
    name="mycheck",
    parse_function=parse_mycheck,
    host_label_function=host_label_mycheck,
)
```

## Multiple Sections

Subscribe to multiple sections:

```python
check_plugin_combined = CheckPlugin(
    name="combined_check",
    sections=["section_a", "section_b"],
    service_name="Combined %s",
    discovery_function=discover_combined,
    check_function=check_combined,
)

def check_combined(item, section_section_a, section_section_b):
    # Access each section by name prefixed with section_
    pass
```

## Debugging

```python
# Enable debug output (remove in production!)
try:
    from cmk.ccc import debug
except ImportError:
    from cmk.utils import debug
from pprint import pprint

def check_mycheck(section):
    if debug.enabled():
        pprint(section)
    # ...
```
