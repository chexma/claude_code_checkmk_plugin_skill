---
name: checkmk-plugin-dev
description: >
  This skill should be used when the user asks to "create a CheckMK plugin",
  "build a check plugin", "write an SNMP check", "create a special agent",
  "add metrics to a check", "create a ruleset", "package an MKP",
  "migrate a legacy plugin", or mentions CheckMK 2.4 plugin development,
  agent-based checks, rulesets API, graphing API, or bakery API.
---

# CheckMK 2.4 Plugin Development

Comprehensive guidance for developing CheckMK 2.4 monitoring plugins using current APIs.

## Choose Your Path

| To accomplish... | Start here | Template |
|---|---|---|
| Monitor a REST API (cloud, app) | `references/special_agents.md` | `datasource_complete.py` |
| Monitor network devices (SNMP) | `references/snmp_api.md` | `snmp_check.py` |
| Process agent output | `references/agent_based_api.md` | `agent_check_simple.py` |
| Check network services (HTTP/TCP) | `references/active_checks.md` | `active_check_executable.py` |
| Run scripts on monitored hosts | `references/agent_plugins.md` | `linux_agent_plugin.py` |
| Create simplest host-side check | `references/local_checks.md` | `local_check.py` |
| Monitor VMs/containers | `references/piggyback_api.md` | `datasource_complete.py` |
| Distribute plugins via Agent Bakery | `references/bakery_api.md` | `bakery_plugin.py` |
| Package for distribution | `references/mkp_packaging.md` | - |
| Migrate existing Nagios plugin | `references/migration_guide.md` | - |

## Core APIs

| API | Import | Purpose |
|-----|--------|---------|
| Check API V2 | `cmk.agent_based.v2` | Agent-based and SNMP checks |
| Rulesets API V1 | `cmk.rulesets.v1` | Rule configuration forms |
| Graphing API V1 | `cmk.graphing.v1` | Metrics, graphs, perfometers |
| Server-Side Calls | `cmk.server_side_calls.v1` | Special agents and active checks |

## Directory Structure

Place all plugins under `~/local/lib/python3/cmk_addons/plugins/<family_name>/`:

```
<family_name>/
├── agent_based/       # Check plugins (agent & SNMP)
├── rulesets/          # Rule definitions
├── graphing/          # Metrics, graphs, perfometers
├── server_side_calls/ # Special agent configs
├── libexec/           # Special agent executables
└── checkman/          # Man pages
```

## Variable Naming (CRITICAL)

Plugins are discovered by variable name prefix:

| Prefix | Type |
|--------|------|
| `agent_section_` | Agent sections |
| `snmp_section_` | SNMP sections |
| `check_plugin_` | Check plugins |
| `rule_spec_` | Ruleset specifications |
| `metric_`, `graph_`, `perfometer_` | Graphing elements |
| `special_agent_`, `active_check_` | Server-side calls |

## Quick Start Example

```python
#!/usr/bin/env python3
from cmk.agent_based.v2 import (
    AgentSection, CheckPlugin, Service, Result, State, check_levels, render
)

def parse_mycheck(string_table):
    return {line[0]: {"value": int(line[1])} for line in string_table}

def discover_mycheck(section):
    for item in section:
        yield Service(item=item)

def check_mycheck(item, params, section):
    if not (data := section.get(item)):
        return
    yield from check_levels(
        data["value"],
        levels_upper=params.get("levels_upper"),
        metric_name="mymetric",
        label="Value",
        render_func=render.percent,
    )

agent_section_mycheck = AgentSection(name="mycheck", parse_function=parse_mycheck)

check_plugin_mycheck = CheckPlugin(
    name="mycheck",
    service_name="My Check %s",
    discovery_function=discover_mycheck,
    check_function=check_mycheck,
    check_default_parameters={"levels_upper": ("fixed", (80.0, 90.0))},
    check_ruleset_name="mycheck",
)
```

## check_levels() Format (CRITICAL)

```python
# CORRECT formats:
levels_upper=("fixed", (warn, crit))    # Fixed thresholds
levels_upper=("no_levels", None)        # Explicitly disabled
levels_upper=None                       # No levels

# WRONG - causes TypeError:
levels_upper=(warn, crit)               # Missing level type!
```

`SimpleLevels` from Rulesets API produces the correct format - pass directly to `check_levels()`.

## Testing Commands

```bash
cmk -vI --detect-plugins=myplugin hostname    # Discovery
cmk -v --detect-plugins=myplugin hostname     # Execute check
cmk --debug --detect-plugins=myplugin hostname # Debug mode
cmk -D hostname                                # Show effective params
omd restart apache                             # After ruleset/graphing changes
```

## Reference Files

### Getting Started
- `references/development_overview.md` - Extension type decision tree
- `references/api_overview.md` - Complete API ecosystem

### Core APIs
- `references/agent_based_api.md` - Check API V2 details, TypedDict patterns
- `references/rulesets_api.md` - Form specs, factory functions
- `references/graphing_api.md` - Metrics, graphs, perfometers
- `references/snmp_api.md` - SNMP detection & OID handling
- `references/special_agents.md` - REST API integration

### Advanced Topics
- `references/piggyback_api.md` - Multi-host data (VMs, containers)
- `references/bakery_api.md` - Agent Bakery distribution
- `references/active_checks.md` - Network service checks
- `references/agent_plugins.md` - Host-side scripts
- `references/local_checks.md` - Simplest host-side checks
- `references/inventory_api.md` - HW/SW inventory
- `references/host_labels.md` - Auto-assign labels
- `references/mkp_packaging.md` - Package distribution
- `references/migration_guide.md` - Legacy plugin migration
- `references/best_practices.md` - Testing, debugging, crash analysis
- `references/checkman_manpages.md` - Man page format

## Templates

Ready-to-use templates in `assets/templates/`:

### First Plugin
1. `agent_check_simple.py` → 2. `ruleset.py` → 3. `graphing.py`

### REST API Monitoring
1. `datasource_complete.py` → 2. `datasource_server_side_calls.py` → 3. `datasource_ruleset.py`

### SNMP Monitoring
`snmp_check.py` (5 examples), `snmp_check_multitable.py`

### Active Checks
1. `active_check_executable.py` → 2. `active_check_server_side_calls.py` → 3. `active_check_ruleset.py`

### Host-Side Collection
`linux_agent_plugin.py`, `linux_agent_plugin.sh`, `windows_agent_plugin.ps1`

### Local Checks
`local_check.py`, `local_check_linux.sh`, `local_check_windows.ps1`

### Bakery Distribution
1. `bakery_plugin.py` → 2. `bakery_ruleset.py`

## Common Patterns

### Render Functions
```python
render.percent(50.5)      # "50.50%"
render.bytes(1024)        # "1.00 KiB"
render.timespan(3661)     # "1 hour 1 minute"
render.datetime(ts)       # "Jan 01 2024, 12:00:00"
```

### State Evaluation
```python
yield Result(state=State.OK, summary="Status text")
yield Result(state=State.WARN, summary="Warning", details="Extended info")
```

## In-CheckMK Documentation

Access via **Help > Developer resources** for Sphinx API docs, REST API ReDoc, and Swagger UI.
