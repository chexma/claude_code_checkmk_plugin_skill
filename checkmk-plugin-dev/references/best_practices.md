# CheckMK Plugin Development Best Practices

## Naming Conventions

### Plugin Names
- Use lowercase letters, digits, and underscores only: `my_check_plugin`
- Use descriptive prefixes for organization: `cisco_`, `linux_`, `aws_`
- Check existing names: `cmk -L | grep -i myprefix`

### Variable Naming (CRITICAL)
Plugins are discovered by prefix:
```python
agent_section_mycheck = AgentSection(...)      # Starts with agent_section_
snmp_section_mycheck = SimpleSNMPSection(...)  # Starts with snmp_section_
check_plugin_mycheck = CheckPlugin(...)        # Starts with check_plugin_
rule_spec_mycheck = CheckParameters(...)       # Starts with rule_spec_
metric_mycheck = Metric(...)                   # Starts with metric_
graph_mycheck = Graph(...)                     # Starts with graph_
perfometer_mycheck = Perfometer(...)           # Starts with perfometer_
```

### File Organization
```
~/local/lib/python3/cmk_addons/plugins/
└── mycompany_checks/           # Family name (your organization/project)
    ├── agent_based/
    │   ├── mycheck.py          # Main check plugin
    │   └── mycheck_extended.py # Additional related checks
    ├── rulesets/
    │   └── mycheck.py          # Ruleset definitions
    └── graphing/
        └── mycheck.py          # Metrics and perfometers
```

## Common Gotchas

### Result() Requires summary or notice

**This will crash your plugin!**

```python
# WRONG - CRASHES with TypeError!
yield Result(state=State.OK, details="Extended info only")
# TypeError: at least 'summary' or 'notice' is required

# CORRECT
yield Result(state=State.OK, summary="Status text")
yield Result(state=State.OK, notice="Shows in details, summary only when not OK")
yield Result(state=State.OK, summary="Short", details="Extended info")
```

The `details` parameter alone is **never valid**. Always provide `summary` or `notice`.

## Parse Function Best Practices

### Always Return Dictionary for Performance
```python
# Good: O(1) lookup
def parse_mycheck(string_table):
    parsed = {}
    for line in string_table:
        key = line[0]
        parsed[key] = {"value": line[1], "status": line[2]}
    return parsed

# Bad: O(n) search for each item
def parse_mycheck(string_table):
    return string_table  # Raw list requires linear search
```

### Handle Empty/Invalid Data
```python
def parse_mycheck(string_table):
    if not string_table:
        return None  # Plugin won't run
    
    parsed = {}
    for line in string_table:
        if len(line) < 3:
            continue  # Skip malformed lines
        try:
            parsed[line[0]] = {
                "value": float(line[1]),
                "status": int(line[2]),
            }
        except (ValueError, IndexError):
            continue  # Skip unparseable lines
    
    return parsed if parsed else None
```

## Check Function Best Practices

### Use check_levels() for Thresholds
```python
# Good: Works with Rulesets API, includes metric
yield from check_levels(
    value,
    levels_upper=params.get("levels_upper"),
    metric_name="mymetric",
    label="CPU Usage",
    render_func=render.percent,
    boundaries=(0.0, 100.0),
)

# Avoid: Manual threshold checking
if value >= crit:
    yield Result(state=State.CRIT, ...)
elif value >= warn:
    yield Result(state=State.WARN, ...)
```

### Handle Missing Items Gracefully
```python
def check_mycheck(item, section):
    data = section.get(item)
    if not data:
        # Option 1: Let CheckMK handle it (shows "Item not found")
        return
        
        # Option 2: Custom message
        yield Result(
            state=State.UNKNOWN,
            summary=f"Item '{item}' no longer exists"
        )
        return
```

### Keep Summary Short
```python
# Good: Under 60 characters
yield Result(
    state=State.OK,
    summary="15 hosts UP",
    details="Hosts: host1, host2, host3, host4, host5, ..."
)

# Bad: Long summary
yield Result(
    state=State.OK,
    summary="All hosts are UP: host1, host2, host3, host4, host5, ..."
)
```

### Use notice_only for Conditional Display
```python
# Shows in summary only when not OK
yield from check_levels(
    value,
    levels_upper=params.get("levels"),
    metric_name="metric",
    label="Value",
    notice_only=True,  # Hidden in summary when OK
)
```

## Default Parameters

### Always Provide Defaults
```python
check_plugin_mycheck = CheckPlugin(
    name="mycheck",
    # ...
    check_default_parameters={
        "levels_upper": ("fixed", (80.0, 90.0)),
        "levels_lower": ("fixed", (10.0, 5.0)),
        "include_feature": True,
    },
    check_ruleset_name="mycheck",
)
```

### Access Parameters Safely
```python
def check_mycheck(item, params, section):
    # Safe access with defaults
    levels = params.get("levels_upper")  # Returns None if not set
    timeout = params.get("timeout", 30)  # Returns 30 if not set
    enabled = params.get("enabled", True)
```

## Testing Workflow

### Development Cycle
```bash
# 1. Edit plugin files

# 2. Test syntax
python3 -m py_compile ~/local/lib/python3/cmk_addons/plugins/mycheck/agent_based/mycheck.py

# 3. Restart if needed (rulesets/graphing)
omd restart apache

# 4. Test discovery
cmk -vI --detect-plugins=mycheck myhostname

# 5. Test check execution
cmk -v --detect-plugins=mycheck myhostname

# 6. Debug mode for errors
cmk --debug --detect-plugins=mycheck myhostname

# 7. Activate changes
cmk -R
```

### Using Spool Files for Testing
Create test data in `/var/lib/check_mk_agent/spool/`:
```bash
cat > /var/lib/check_mk_agent/spool/mycheck <<EOF
<<<mycheck>>>
item1;100;OK
item2;50;WARNING
item3;10;CRITICAL
EOF
```

### Debug Output (Development Only)
```python
try:
    from cmk.ccc import debug
except ImportError:
    from cmk.utils import debug
from pprint import pprint

def check_mycheck(section):
    if debug.enabled():
        pprint(section)
    # ... rest of check
```

**Remove debug output before deployment!**

## Error Handling

### Let Exceptions Propagate for Debugging
```python
# Good: Exception creates crash report with full context
def parse_mycheck(string_table):
    parsed = {}
    for foo, bar, baz in string_table:  # Fails if not 3 elements
        parsed[foo] = {"bar": bar, "baz": baz}
    return parsed

# Avoid: Silent failures hide bugs
def parse_mycheck(string_table):
    parsed = {}
    for line in string_table:
        try:
            parsed[line[0]] = {"bar": line[1], "baz": line[2]}
        except:
            pass  # Silent failure - hard to debug
    return parsed
```

### Expected Missing Data vs Errors
```python
def check_mycheck(item, section):
    data = section.get(item)
    
    # Expected: Item might not exist
    if not data:
        return  # Let CheckMK handle
    
    # Unexpected: Data structure wrong (programming error)
    value = data["value"]  # KeyError = crash report = good!
```

## Performance Considerations

### Parse Once, Check Many
The parse function runs once per host, check function runs per service.
Do expensive operations in parse function:

```python
def parse_mycheck(string_table):
    parsed = {}
    for line in string_table:
        # Do parsing, type conversion, validation here
        parsed[line[0]] = {
            "value": float(line[1]),
            "normalized": float(line[1]) / 100.0,
            "timestamp": int(line[2]),
        }
    return parsed

def check_mycheck(item, section):
    # Check function just reads pre-processed data
    data = section.get(item)
    # ...
```

### Avoid Excessive Services
```python
def discover_mycheck(section):
    for item, data in section.items():
        # Filter during discovery, not during check
        if data.get("is_active"):
            yield Service(item=item)
```

## Migration from API V1 to V2

### Key Changes
| V1 | V2 |
|----|-----|
| `register.agent_section()` | `AgentSection(...)` class |
| `register.check_plugin()` | `CheckPlugin(...)` class |
| `register.snmp_section()` | `SimpleSNMPSection(...)` or `SNMPSection(...)` |
| `local/lib/check_mk/base/plugins/agent_based/` | `local/lib/python3/cmk_addons/plugins/<family>/agent_based/` |
| `from .agent_based_api.v1 import *` | `from cmk.agent_based.v2 import ...` |
| `type_defs` module | Types in `cmk.agent_based.v2` |
| `SNMPDetect` class | Detection functions (`startswith`, `contains`, etc.) |

### Migration Steps
1. Create new directory structure
2. Update imports
3. Convert registration to class instantiation
4. Rename variables with correct prefixes
5. Test thoroughly
6. Remove old files

### Migration Helper Scripts
Available at: `github.com/Checkmk/checkmk/tree/master/doc/treasures/migration_helpers/`

## Packaging as MKP

```bash
# List unpackaged files
mkp find

# Create package
mkp template mycheck > /tmp/mycheck.json
# Edit the JSON file
mkp package /tmp/mycheck.json

# Install package
mkp add mycheck-1.0.0.mkp

# Enable package
mkp enable mycheck 1.0.0
```

Package JSON structure:
```json
{
    "name": "mycheck",
    "version": "1.0.0",
    "version.min_required": "2.3.0",
    "version.usable_until": "2.5.99",
    "title": "My Check Plugin",
    "author": "Your Name",
    "description": "Description of the plugin",
    "files": {
        "cmk_addons_plugins": [
            "mycheck/agent_based/mycheck.py",
            "mycheck/rulesets/mycheck.py",
            "mycheck/graphing/mycheck.py"
        ],
        "agents": [
            "plugins/mycheck"
        ]
    }
}
```
