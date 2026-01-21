---
name: checkmk-plugin-dev
description: >
  CheckMK 2.4 plugin development with 20 references, 17 templates, and decision trees.
  For agent-based checks, SNMP plugins, special agents, active checks, rulesets,
  metrics, inventory, and MKP packaging. Use when: creating CheckMK plugins, building
  custom checks, packaging extensions, migrating legacy plugins, or configuring agent bakery.
  NOT for: REST API client code, CheckMK core development, or real-time alerting webhooks.
---

# CheckMK 2.4 Plugin Development

## Quick Navigation

- [Choose Your Path](#choose-your-path) - Start here based on your use case
- [Directory Structure](#directory-structure-checkmk-24)
- [Variable Naming (CRITICAL)](#variable-naming-prefixes-critical)
- [Quick Start Example](#quick-start-agent-based-check-plugin)
- [Testing Commands](#testing-commands)
- [Reference Files](#reference-files)
- [Templates by Use Case](#templates-by-use-case)
- [Key Imports](#key-imports-by-api)
- [Common Patterns](#common-patterns)

## Choose Your Path

### By Use Case

| If you want to... | Start here | Template |
|---|---|---|
| Monitor a REST API (cloud, app) | `references/special_agents.md` | `datasource_complete.py` |
| Monitor network devices (SNMP) | `references/snmp_api.md` | `snmp_check.py` |
| Process agent output | `references/agent_based_api.md` | `agent_check_simple.py` |
| Check network services (HTTP/TCP) | `references/active_checks.md` | `active_check_executable.py` |
| Run scripts on monitored hosts | `references/agent_plugins.md` | `linux_agent_plugin.py` |
| Simplest host-side check | `references/local_checks.md` | `local_check.py` |
| Monitor VMs/containers | `references/piggyback_api.md` | `datasource_complete.py` |
| Distribute plugins via UI | `references/bakery_api.md` | `bakery_plugin.py` |
| Package for distribution | `references/mkp_packaging.md` | - |

### By Starting Point

| If you have... | Start here |
|---|---|
| Existing Nagios plugin | `references/migration_guide.md` |
| REST API to monitor | `references/special_agents.md` |
| Network device (SNMP) | `references/snmp_api.md` |
| Questions about thresholds/rules | `references/rulesets_api.md` |
| Multi-host data (VMs, containers) | `references/piggyback_api.md` |

### API Combinations by Plugin Type

| Plugin Type | APIs Needed |
|---|---|
| Agent-based check | Check API V2 + Rulesets API V1 + (optional) Graphing API V1 |
| Special agent | Server-Side Calls API + Check API V2 + Rulesets API V1 |
| Active check | Server-Side Calls API + (optional) Rulesets API V1 |
| SNMP check | Check API V2 (SNMPSection) + Rulesets API V1 |

## Overview

This skill provides comprehensive guidance for developing CheckMK 2.4 plugins using current APIs:

### Core APIs
- **Check API V2** (`cmk.agent_based.v2`) - Agent-based and SNMP check plugins
- **Rulesets API V1** (`cmk.rulesets.v1`) - Rule configuration for check parameters
- **Graphing API V1** (`cmk.graphing.v1`) - Metrics, graphs, and perfometers
- **Server-Side Calls API** (`cmk.server_side_calls.v1`) - Special agents and active checks

### Advanced Topics
- **Piggyback** - Multi-host monitoring (VMs, containers, cloud resources)
- **Inventory Plugins** - Hardware/Software inventory collection
- **Agent Plugins** - Scripts running on monitored hosts (with server-side check plugin)
- **Local Checks** - Simplest host-side scripts (status determined in script, no server plugin needed)
- **Spool Directory** - External programs writing agent output to files
- **Bakery API** - Distribute agent plugins via Agent Bakery (commercial editions)
- **MKP Packaging** - Creating and distributing extension packages

## Directory Structure (CheckMK 2.4)

All plugins go under `~/local/lib/python3/cmk_addons/plugins/<family_name>/`:

```
~/local/lib/python3/cmk_addons/plugins/
└── <family_name>/
    ├── agent_based/      # Check plugins (agent & SNMP)
    ├── rulesets/         # Rule definitions
    ├── graphing/         # Metrics, graphs, perfometers
    ├── server_side_calls/ # Special agent configs
    ├── libexec/          # Special agent executables
    └── checkman/         # Man pages
```

## Variable Naming Prefixes (CRITICAL)

Plugins are discovered by name prefix:
- `agent_section_` - Agent sections
- `snmp_section_` - SNMP sections
- `check_plugin_` - Check plugins
- `inventory_plugin_` - Inventory plugins
- `rule_spec_` - Ruleset specifications
- `metric_` - Metric definitions
- `graph_` - Graph definitions
- `perfometer_` - Perfometer definitions
- `special_agent_` - Special agent configs
- `active_check_` - Active check configs

## Quick Start: Agent-Based Check Plugin

```python
#!/usr/bin/env python3
from cmk.agent_based.v2 import (
    AgentSection, CheckPlugin, Service, Result, State,
    Metric, check_levels, render
)

def parse_mycheck(string_table):
    parsed = {}
    for line in string_table:
        parsed[line[0]] = {"value": int(line[1])}
    return parsed

def discover_mycheck(section):
    for item in section:
        yield Service(item=item)

def check_mycheck(item, params, section):
    data = section.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary="Item not found")
        return

    yield from check_levels(
        data["value"],
        levels_upper=params.get("levels_upper"),
        metric_name="mymetric",
        label="Value",
        render_func=render.percent,
    )

agent_section_mycheck = AgentSection(
    name="mycheck",
    parse_function=parse_mycheck,
)

check_plugin_mycheck = CheckPlugin(
    name="mycheck",
    service_name="My Check %s",
    discovery_function=discover_mycheck,
    check_function=check_mycheck,
    check_default_parameters={"levels_upper": ("fixed", (80.0, 90.0))},
    check_ruleset_name="mycheck",
)

# Expected output in CheckMK:
# Service: "My Check item1"
# Status: OK - Value: 42.50%
# Perfdata: mymetric=42.5;80.0;90.0
```

## Testing Commands

Test your plugin after each change:

```bash
# Service discovery
cmk -vI --detect-plugins=myplugin hostname

# Execute check
cmk -v --detect-plugins=myplugin hostname

# Debug mode (shows stack traces)
cmk --debug --detect-plugins=myplugin hostname

# Show effective parameters per service
cmk -D hostname

# Restart after ruleset/graphing changes
omd restart apache

# Restart core after check changes
cmk -R
```

## Reference Files

For detailed information, read the appropriate reference file:

### Getting Started
- **Development Overview**: `references/development_overview.md` - Which extension type to use, decision tree, comparison
- **API Overview**: `references/api_overview.md` - Complete API ecosystem, imports, naming conventions

### Core APIs
- **Agent-based plugins**: `references/agent_based_api.md` - Check API V2 details
- **Host Labels**: `references/host_labels.md` - Auto-assign labels during discovery
- **SNMP plugins**: `references/snmp_api.md` - SNMP detection & OID handling
- **Rulesets**: `references/rulesets_api.md` - Form specs & rule definitions
- **Graphing/Metrics**: `references/graphing_api.md` - Metrics, graphs, perfometers
- **Special agents**: `references/special_agents.md` - REST API integration (Datasource Programs)

### Advanced Topics
- **Piggyback**: `references/piggyback_api.md` - Multi-host data (VMs, containers, cloud resources)
- **Inventory Plugins**: `references/inventory_api.md` - HW/SW inventory collection
- **Agent Plugins**: `references/agent_plugins.md` - Scripts running on monitored hosts (require server-side check plugin)
- **Local Checks**: `references/local_checks.md` - Simplest host-side scripts (no server plugin needed)
- **Spool Directory**: `references/spool_directory.md` - External programs writing agent output to files
- **Active Checks**: `references/active_checks.md` - Server-side network service checks (HTTP, TCP, etc.)
- **Bakery API**: `references/bakery_api.md` - Distribute plugins via Agent Bakery (commercial editions)
- **MKP Packaging**: `references/mkp_packaging.md` - Creating distributable packages
- **Man Pages**: `references/checkman_manpages.md` - Check plugin documentation
- **Migration Guide**: `references/migration_guide.md` - Migrating legacy plugins to current APIs
- **Best practices**: `references/best_practices.md` - Testing, debugging, crash analysis

## Templates by Use Case

Ready-to-use templates in `assets/templates/`:

### First Plugin (Start Here)
1. `agent_check_simple.py` - Minimal agent-based check
2. `ruleset.py` - Add configurable parameters
3. `graphing.py` - Add metrics and perfometers

### REST API Monitoring (Special Agent)
1. `datasource_complete.py` - Full special agent with API client
2. `datasource_server_side_calls.py` - Server-side configuration
3. `datasource_ruleset.py` - GUI parameters

### SNMP Monitoring
1. `snmp_check.py` - 5 examples (scalar, table, metrics, rates, detection)
2. `snmp_check_multitable.py` - Multi-table correlation (ifTable + ifXTable)

### Network Service Checks (Active Checks)
1. `active_check_executable.py` - Nagios-compatible executable
2. `active_check_server_side_calls.py` - ActiveCheckConfig
3. `active_check_ruleset.py` - Rule specification

### Host-Side Data Collection
- `linux_agent_plugin.py` - Python plugin with config, sections, piggyback
- `linux_agent_plugin.sh` - Bash plugin with config
- `windows_agent_plugin.ps1` - PowerShell with WMI, registry

### Simplest Checks (Local Checks)
- `local_check.py` - Cross-platform Python
- `local_check_linux.sh` - Bash template
- `local_check_windows.ps1` - PowerShell template

### Plugin Distribution (Bakery)
1. `bakery_plugin.py` - Files, scriptlets, Windows config
2. `bakery_ruleset.py` - AgentConfig ruleset

## Key Imports by API

### Check API V2
```python
from cmk.agent_based.v2 import (
    AgentSection, CheckPlugin, InventoryPlugin,
    SimpleSNMPSection, SNMPSection, SNMPTree,
    Service, Result, State, Metric,
    check_levels, render, StringTable,
    startswith, contains, matches, exists,
    all_of, any_of, not_startswith, not_contains,
)
```

### Rulesets API V1
```python
from cmk.rulesets.v1 import Title, Label, Help
from cmk.rulesets.v1.form_specs import (
    Dictionary, DictElement, String, Integer, Float,
    SimpleLevels, LevelDirection, DefaultValue,
    BooleanChoice, SingleChoice, SingleChoiceElement,
    Password, migrate_to_password,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters, HostCondition, HostAndItemCondition,
    Topic, SpecialAgent,
)
```

### Graphing API V1
```python
from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import Metric, Color, Unit, DecimalNotation
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.perfometers import Perfometer, FocusRange, Closed, Open
```

## In-CheckMK Documentation

Access via **Help > Developer resources**:
- **Plug-in API references** - Full Sphinx docs for all APIs
- **REST API documentation** - ReDoc with code examples
- **REST API interactive GUI** - Swagger UI for testing

## Common Patterns

### check_levels() with Ruleset Integration
```python
# In check function - works with SimpleLevels from rulesets
yield from check_levels(
    value,
    levels_upper=params.get("levels_upper"),  # ("fixed", (warn, crit))
    levels_lower=params.get("levels_lower"),
    metric_name="mymetric",
    label="Temperature",
    render_func=render.temp,
    boundaries=(0.0, 100.0),
)
```

### State Evaluation
```python
from cmk.agent_based.v2 import State, Result

# Simple states
yield Result(state=State.OK, summary="All good")
yield Result(state=State.WARN, summary="Warning condition")
yield Result(state=State.CRIT, summary="Critical!")
yield Result(state=State.UNKNOWN, summary="Cannot determine")

# With details (shown only in service details, not summary)
yield Result(
    state=State.OK,
    summary="Short status",
    details="Extended information for details view"
)
```

### Render Functions
```python
from cmk.agent_based.v2 import render

render.percent(50.5)      # "50.50%"
render.bytes(1024)        # "1.00 KiB"
render.disksize(1000000)  # "1.00 MB" (base 1000)
render.timespan(3661)     # "1 hour 1 minute"
render.datetime(ts)       # "Jan 01 2024, 12:00:00"
render.networkbandwidth(1000000)  # "8.00 MBit/s"
render.iobandwidth(1000000)       # "1.00 MB/s"
```
