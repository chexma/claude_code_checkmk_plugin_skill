# Migration Guide: Legacy Plugins to CheckMK 2.4 APIs

This guide covers migrating older CheckMK plugins to the current APIs. CheckMK provides migration helper scripts in the repository.

## Migration Paths Overview

| From | To | Script |
|------|-----|--------|
| Check API v1 | Check API v2 | `agent_based_v1_v2.py` |
| Legacy checks (`check_info`) | Check API v2 | `legacy_checks_to_v2.py` |
| Legacy ValueSpecs | Rulesets API v1 | `legacy_vs_to_ruleset_v1.py` |
| Legacy graphing (`metric_info`) | Graphing API v1 | `graphing_v0_v1.py` |
| Legacy special agents | Server-Side Calls v1 | `legacy_ssc_to_v1.py` |

## Getting the Migration Scripts

```bash
# Download from CheckMK repository
wget https://raw.githubusercontent.com/Checkmk/checkmk/release/2.4.0p16/doc/treasures/migration_helpers/agent_based_v1_v2.py
wget https://raw.githubusercontent.com/Checkmk/checkmk/release/2.4.0p16/doc/treasures/migration_helpers/legacy_checks_to_v2.py
wget https://raw.githubusercontent.com/Checkmk/checkmk/release/2.4.0p16/doc/treasures/migration_helpers/legacy_vs_to_ruleset_v1.py
wget https://raw.githubusercontent.com/Checkmk/checkmk/release/2.4.0p16/doc/treasures/migration_helpers/graphing_v0_v1.py
wget https://raw.githubusercontent.com/Checkmk/checkmk/release/2.4.0p16/doc/treasures/migration_helpers/legacy_ssc_to_v1.py

# Install required dependency
pip install libcst
```

## Important Notes

> **These scripts are not perfect.** They are described as "quick and dirty" helpers developed for internal use. You **must** check and adjust the results manually. For simple plugins they may do the whole job; for most plugins they provide a starting point.

---

## 1. Check API v1 to v2 Migration

### Usage

```bash
python3 agent_based_v1_v2.py [-d] mycheck.py
```

### What It Converts

**Imports:**
```python
# Before (v1)
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    register, Service, Result, State, check_levels
)

# After (v2)
from cmk.agent_based.v2 import (
    AgentSection, CheckPlugin, Service, Result, State, check_levels
)
```

**Registration:**
```python
# Before (v1)
register.agent_section(
    name="mycheck",
    parse_function=parse_mycheck,
)

register.check_plugin(
    name="mycheck",
    service_name="My Check %s",
    discovery_function=discover_mycheck,
    check_function=check_mycheck,
)

# After (v2)
agent_section_mycheck = AgentSection(
    name="mycheck",
    parse_function=parse_mycheck,
)

check_plugin_mycheck = CheckPlugin(
    name="mycheck",
    service_name="My Check %s",
    discovery_function=discover_mycheck,
    check_function=check_mycheck,
)
```

### Manual Steps After Script

1. Verify all imports are correct
2. Check that variable naming follows `agent_section_`, `check_plugin_` prefixes
3. Update type hints: `list[StringTable]` → `Sequence[StringTable]`
4. Test the migrated plugin

---

## 2. Legacy Checks (`check_info`) to v2

### Usage

```bash
python3 legacy_checks_to_v2.py [-d] old_check.py
```

### What It Converts

**Check Registration:**
```python
# Before (legacy)
check_info["mycheck"] = {
    "check_function": check_mycheck,
    "inventory_function": inventory_mycheck,
    "service_description": "My Check %s",
    "has_perfdata": True,
}

# After (v2)
check_plugin_mycheck = CheckPlugin(
    name="mycheck",
    service_name="My Check %s",
    discovery_function=discover_mycheck,
    check_function=check_mycheck,
)
```

**Discovery Functions:**
```python
# Before (legacy) - returns list of tuples
def inventory_mycheck(info):
    return [(item, {}) for item in info]

# After (v2) - generator yielding Service objects
def discover_mycheck(section):
    for item in section:
        yield Service(item=item)
```

**Check Functions:**
```python
# Before (legacy) - returns tuple
def check_mycheck(item, params, info):
    return (0, "OK - everything fine", [("metric", 42)])

# After (v2) - generator yielding Result/Metric
def check_mycheck(item, params, section):
    yield Result(state=State.OK, summary="OK - everything fine")
    yield Metric("metric", 42)
```

**State Mapping:**
| Legacy | v2 |
|--------|-----|
| `0` | `State.OK` |
| `1` | `State.WARN` |
| `2` | `State.CRIT` |
| `3` | `State.UNKNOWN` |

### Manual Steps After Script

1. Update function parameter names (`info`/`parsed` → `section`)
2. Add type annotations
3. Convert SNMP sections with proper detection
4. Create separate AgentSection/SNMPSection definitions
5. Move file to `~/local/lib/python3/cmk_addons/plugins/<family>/agent_based/`

---

## 3. Legacy ValueSpecs to Rulesets API v1

### Usage

```bash
python3 legacy_vs_to_ruleset_v1.py [-d] old_wato.py
```

### What It Converts

**Imports:**
```python
# Before (legacy)
from cmk.gui.valuespec import Dictionary, TextInput, Integer, Checkbox
from cmk.gui.plugins.wato import CheckParameterRulespec

# After (v1)
from cmk.rulesets.v1 import Title, Help
from cmk.rulesets.v1.form_specs import Dictionary, String, Integer, BooleanChoice
from cmk.rulesets.v1.rule_specs import CheckParameters
```

**Form Spec Mappings:**

| Legacy ValueSpec | New Form Spec |
|-----------------|---------------|
| `Dictionary` | `Dictionary` |
| `TextInput` | `String` |
| `Integer` | `Integer` |
| `Float` | `Float` |
| `Checkbox` | `BooleanChoice` |
| `DropdownChoice` | `SingleChoice` |
| `CascadingDropdown` | `CascadingSingleChoice` |
| `ListOf` | `List` |
| `Tuple` | `Dictionary` or `Tuple` |
| `IndividualOrStoredPassword` | `Password` |
| `Age` / `TimeSpan` | `TimeSpan` |

**Rule Spec Mappings:**

| Legacy | New |
|--------|-----|
| `CheckParameterRulespec` | `CheckParameters` |
| `HostRulespec` (ActiveChecks) | `ActiveCheck` |
| `HostRulespec` (SpecialAgents) | `SpecialAgent` |

**Parameter Mappings:**
```python
# Before (legacy)
Dictionary(
    title="My Settings",
    help="Help text here",
    elements=[
        ("threshold", Integer(title="Threshold", default_value=80)),
    ],
)

# After (v1)
Dictionary(
    title=Title("My Settings"),
    help_text=Help("Help text here"),
    elements={
        "threshold": DictElement(
            parameter_form=Integer(
                title=Title("Threshold"),
                prefill=DefaultValue(80),
            ),
        ),
    },
)
```

### Manual Steps After Script

1. Wrap strings with `Title()`, `Help()`, `Label()`
2. Convert `default_value` to `prefill=DefaultValue(...)`
3. Add validators where needed
4. Move file to `~/local/lib/python3/cmk_addons/plugins/<family>/rulesets/`

---

## 4. Legacy Graphing to Graphing API v1

### Usage

```bash
python3 graphing_v0_v1.py [OPTIONS] folder/
```

**Options:**
- `-d, --debug`: Stop at first exception
- `--cmk-header`: Add CheckMK copyright header
- `--filter-metric-names`: Filter by metric names
- `--translations`: Include translation data
- `--balance-colors`: Auto-assign metric colors

### What It Converts

**Metrics:**
```python
# Before (legacy)
metric_info["my_metric"] = {
    "title": "My Metric",
    "unit": "count",
    "color": "31/a",
}

# After (v1)
metric_my_metric = Metric(
    name="my_metric",
    title=Title("My Metric"),
    unit=Unit.COUNT,
    color=Color.BLUE,
)
```

**Perfometers:**
```python
# Before (legacy)
perfometer_info.append({
    "type": "linear",
    "segments": ["my_metric"],
    "total": 100,
})

# After (v1)
perfometer_my_metric = Perfometer(
    name="my_metric",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["my_metric"],
)
```

**Graphs:**
```python
# Before (legacy)
graph_info["my_graph"] = {
    "title": "My Graph",
    "metrics": [
        ("metric1", "area"),
        ("metric2", "line"),
    ],
}

# After (v1)
graph_my_graph = Graph(
    name="my_graph",
    title=Title("My Graph"),
    compound_lines=["metric1"],
    simple_lines=["metric2"],
)
```

### Manual Steps After Script

1. Review color assignments
2. Verify unit conversions
3. Check perfometer ranges
4. Move file to `~/local/lib/python3/cmk_addons/plugins/<family>/graphing/`

---

## 5. Legacy Server-Side Calls to v1

### Usage

```bash
python3 legacy_ssc_to_v1.py [-d] old_special_agent.py
```

### What It Converts

**Special Agents:**
```python
# Before (legacy)
special_agent_info["myagent"] = agent_myagent_arguments

def agent_myagent_arguments(params, hostname, ipaddress):
    return ["--host", hostname, "--token", params["token"]]

# After (v1)
def generate_myagent_commands(params, host_config):
    yield SpecialAgentCommand(
        command_arguments=["--host", host_config.name, "--token", params["token"]]
    )

special_agent_myagent = SpecialAgentConfig(
    name="myagent",
    parameter_parser=lambda p: p,
    commands_function=generate_myagent_commands,
)
```

**Active Checks:**
```python
# Before (legacy)
active_check_info["mycheck"] = {
    "command_line": "check_mycheck -H $HOSTADDRESS$ $ARG1$",
    "argument_function": check_mycheck_arguments,
}

# After (v1)
def generate_mycheck_commands(params, host_config):
    yield ActiveCheckCommand(
        service_description=params.get("description", "My Check"),
        command_arguments=["-H", host_config.primary_ip_config.address],
    )

active_check_mycheck = ActiveCheckConfig(
    name="mycheck",
    parameter_parser=lambda p: p,
    commands_function=generate_mycheck_commands,
)
```

### Manual Steps After Script

1. Update function signatures to use `HostConfig`
2. Convert return statements to yield generators
3. Handle `Secret` types for passwords
4. Move file to `~/local/lib/python3/cmk_addons/plugins/<family>/server_side_calls/`

---

## Complete Migration Workflow

### Step 1: Identify Legacy Code

```bash
# Find legacy check files
ls ~/local/share/check_mk/checks/

# Find legacy WATO files
ls ~/local/share/check_mk/web/plugins/wato/

# Find legacy graphing files
ls ~/local/share/check_mk/web/plugins/metrics/
```

### Step 2: Create New Plugin Structure

```bash
mkdir -p ~/local/lib/python3/cmk_addons/plugins/myplugin/{agent_based,rulesets,graphing,server_side_calls}
```

### Step 3: Run Migration Scripts

```bash
# Migrate checks
python3 legacy_checks_to_v2.py ~/local/share/check_mk/checks/mycheck
mv output.py ~/local/lib/python3/cmk_addons/plugins/myplugin/agent_based/mycheck.py

# Migrate rulesets
python3 legacy_vs_to_ruleset_v1.py ~/local/share/check_mk/web/plugins/wato/mycheck_params.py
mv output.py ~/local/lib/python3/cmk_addons/plugins/myplugin/rulesets/mycheck.py

# Migrate graphing
python3 graphing_v0_v1.py ~/local/share/check_mk/web/plugins/metrics/ > \
    ~/local/lib/python3/cmk_addons/plugins/myplugin/graphing/metrics.py
```

### Step 4: Manual Review and Testing

```bash
# Syntax check
python3 -m py_compile ~/local/lib/python3/cmk_addons/plugins/myplugin/agent_based/mycheck.py

# Test discovery
cmk -vI --detect-plugins=mycheck testhost

# Test check execution
cmk -v --detect-plugins=mycheck testhost

# Restart services
omd restart apache
cmk -R
```

### Step 5: Remove Legacy Files

```bash
# Only after confirming new plugin works!
rm ~/local/share/check_mk/checks/mycheck
rm ~/local/share/check_mk/web/plugins/wato/mycheck_params.py
```

---

## Common Migration Issues

### Import Errors
```python
# Missing import - add manually
from cmk.agent_based.v2 import Metric, render
```

### Type Annotation Errors
```python
# Change list to Sequence for string_table types
from collections.abc import Sequence
def parse_mycheck(string_table: Sequence[StringTable]) -> dict:
```

### Discovery Not Yielding
```python
# Must yield, not return
def discover_mycheck(section):
    yield Service()  # Correct
    # return [Service()]  # Wrong
```

### State Enum Usage
```python
# Use State enum, not integers
yield Result(state=State.OK, summary="OK")  # Correct
# yield Result(state=0, summary="OK")  # Wrong
```

### Missing Variable Prefix
```python
# Variable names must have correct prefix
check_plugin_mycheck = CheckPlugin(...)  # Correct
# mycheck_plugin = CheckPlugin(...)  # Wrong - won't be discovered
```

## Resources

- [CheckMK Migration Helpers](https://github.com/Checkmk/checkmk/tree/release/2.4.0p16/doc/treasures/migration_helpers)
- [CheckMK Developer Documentation](https://docs.checkmk.com/latest/en/devel_intro.html)
- In CheckMK: **Help > Developer resources**
