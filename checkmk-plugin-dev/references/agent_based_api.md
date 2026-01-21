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

### Parse vs Check Function Timing (IMPORTANT)

> **Problem:** The parse function runs BEFORE the check function, but ruleset parameters are only available in the check function!

If you need ruleset params to affect parsing (e.g., which format to use, what to extract), store raw strings in a dataclass and parse in the check function:

```python
from dataclasses import dataclass
from typing import List

@dataclass
class RawMyCheckData:
    """Store raw strings for deferred parsing."""
    raw_value: str       # Keep as string
    raw_timestamp: str   # Parse in check function with params

def parse_mycheck(string_table: StringTable) -> dict[str, RawMyCheckData] | None:
    if not string_table:
        return None
    parsed = {}
    for line in string_table:
        # Store raw strings, defer parsing to check function
        parsed[line[0]] = RawMyCheckData(
            raw_value=line[1],
            raw_timestamp=line[2] if len(line) > 2 else "",
        )
    return parsed

def check_mycheck(item, params, section):
    data = section.get(item)
    if not data:
        return

    # NOW we have params - parse based on configuration
    date_format = params.get("date_format", "%Y-%m-%d")
    timestamp = datetime.strptime(data.raw_timestamp, date_format)
    # ...
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

### Levels Format (CRITICAL - v2 API)

> **WARNING:** The v2 `check_levels()` function requires a specific tuple format. Using the wrong format causes a `TypeError`!

```python
# CORRECT formats for check_levels():
levels_upper=("fixed", (warn, crit))    # ✅ Fixed thresholds
levels_upper=("no_levels", None)        # ✅ Explicitly disabled
levels_upper=None                       # ✅ No levels configured

# WRONG - causes TypeError!
levels_upper=(warn, crit)               # ❌ Missing level type!
```

**Why this matters:** `SimpleLevels` from the Rulesets API produces `("fixed", (warn, crit))` tuples - pass them directly to `check_levels()` without modification.

```python
# From params dictionary (already in correct format from SimpleLevels)
levels_upper=params.get("cpu_levels")   # Returns ("fixed", (80.0, 90.0)) or None
```

### v1 vs v2 API Note

- `cmk.agent_based.v2` is the current API for CheckMK 2.4
- Some official plugins still use `check_levels_v1` (not yet migrated)
- New plugins should always use v2 `check_levels()` - it's future-proof

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

**IMPORTANT:** `Result()` requires either `summary` or `notice`. Using only `details` will crash!

```python
# WRONG - CRASHES with TypeError!
yield Result(state=State.OK, details="This crashes!")
# TypeError: at least 'summary' or 'notice' is required

# CORRECT - summary is the standard approach
yield Result(
    state=State.OK,
    summary="Short text",        # Always shown (keep under 60 chars)
    details="Extended info",     # Only in service details view
)

# CORRECT - notice: only shows in summary if state != OK
yield Result(
    state=State.OK,
    notice="Hidden when OK, visible in summary when WARN/CRIT",
)

# CORRECT - combine summary with details
yield Result(
    state=State.WARN,
    summary="Brief status",
    details="Extended information shown in service details view",
)
```

| Parameter | Required | Behavior |
|-----------|----------|----------|
| `summary` | Yes* | Always shown in service output |
| `notice` | Yes* | Only in summary when state != OK, always in details |
| `details` | No | Only shown in service details view |

*At least one of `summary` or `notice` is required.

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

Auto-assign labels during discovery. Labels enable automatic host classification based on collected data.

```python
from cmk.agent_based.v2 import AgentSection, HostLabel

def host_label_mycheck(section):
    """Generate host labels from section data."""
    # Identification label
    yield HostLabel("mycheck", "true")

    # Data-based labels
    if section.get("os") == "linux":
        yield HostLabel("mycheck/os", "linux")

    if version := section.get("version"):
        yield HostLabel("mycheck/version", version)

agent_section_mycheck = AgentSection(
    name="mycheck",
    parse_function=parse_mycheck,
    host_label_function=host_label_mycheck,
)
```

### Label Naming Convention
- Use plugin-specific prefix: `{plugin}/key`
- Lowercase keys, no spaces
- Examples: `netapp/version:9.12`, `storage/vendor:NetApp`

### Testing Labels
```bash
cmk -vvII --detect-plugins=mycheck hostname
```

**See:** `references/host_labels.md` for detailed patterns, naming conventions, and usage in rules.

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

## TypedDict for Check Parameters

For better type safety and IDE support, use TypedDict to define parameter structures:

```python
from typing import Literal, TypedDict

# Level type definitions matching Rulesets API output
LevelsType = (
    tuple[Literal["fixed"], tuple[float, float]] |
    tuple[Literal["no_levels"], None] |
    None
)

# Service state as string literal (from SingleChoice elements)
ServiceStateType = Literal["enabled", "disabled"]

class MyCheckParams(TypedDict, total=False):
    """Type definition for check parameters."""
    age_levels: LevelsType
    size_levels: LevelsType
    feature_state: ServiceStateType
    timeout: int

def check_mycheck(item: str, params: MyCheckParams, section) -> CheckResult:
    # IDE provides autocomplete and type checking
    age_levels = params.get("age_levels")
    timeout = params.get("timeout", 30)
    # ...
```

**Benefits:**
- IDE autocomplete for parameter keys
- Type checking catches mismatched parameter names
- Self-documenting code
- Matches `SingleChoiceElement(name="enabled")` patterns in rulesets

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

---

## Related Topics

- **Add configurable parameters** → `rulesets_api.md`
- **Add metrics and graphs** → `graphing_api.md`
- **SNMP-based checks** → `snmp_api.md`
- **Auto-assign host labels** → `host_labels.md`
- **Testing and debugging** → `best_practices.md`
- **Package for distribution** → `mkp_packaging.md`
