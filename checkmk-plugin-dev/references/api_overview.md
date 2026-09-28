# CheckMK API Ecosystem Overview

## Available APIs (CheckMK 2.4 and 2.5)

Unless noted otherwise, these are identical in 2.4 and 2.5:

| API | Purpose | Location |
|-----|---------|----------|
| **REST API v1** | Full automation (hosts, rules, services, downtimes) — stable | `/check_mk/api/v1/`, see `rest_api.md` |
| **Check API V2** | Agent-based & SNMP check plugins | `cmk.agent_based.v2` |
| **Rulesets API V1** | Rule configuration forms | `cmk.rulesets.v1` |
| **Graphing API V1** | Metrics, graphs, perfometers | `cmk.graphing.v1` |
| **Server-side Calls API** | Special agents & active checks | `cmk.server_side_calls.v1` |
| **Bakery API v1** | Agent bakery integration (stable, 2.3–2.4+) | `cmk.base.plugins.bakery.bakery_api.v1` |
| **HW/SW Inventory API** | Hardware/Software inventory (collection) | `cmk.agent_based.v2` (`InventoryPlugin`) |
| **Livestatus** | Real-time status queries | Unix socket / TCP |
| **Local Checks** | Simple script-based checks | Agent output format |

### New in CheckMK 2.5 (all unstable — see `SKILL.md` version note)

| API | Purpose | Location |
|-----|---------|----------|
| **Bakery API v2** | Agent bakery integration, new plugin family layout | `cmk.bakery.v2_unstable` |
| **Password Store API** | Read stored secrets in server-side programs | `cmk.password_store.v1_unstable` |
| **Server-Side Programs API** | Crash reports, call-to-call persistence, TLS helpers | `cmk.server_side_programs.v1_unstable` |
| **Inventory UI API** | Custom HW/SW inventory tree visualizations | `cmk.inventory_ui.v1_unstable` |
| **DCD Connector API** | Custom Dynamic Configuration Daemon connectors (commercial editions, unversioned) | `cmk.nonfree.pro.dcd.connector_api`, see `dcd_connector_api.md` |
| **REST API unstable** | v1 + 50 new endpoints (dashboards, availability, relays, OpenTelemetry, metric backend, inventory trees, …) | `/check_mk/api/unstable/`, see `rest_api.md` |

## In-Checkmk Resources

Access via **Help > Developer resources**:

- **Plug-in API references** - Sphinx documentation for all plugin APIs
- **REST API documentation** - ReDoc/OpenAPI reference with code examples
- **REST API interactive GUI** - Swagger UI for testing endpoints

## API Documentation URLs (in CheckMK)

```
# Plugin API Reference (internal)
https://<server>/<site>/check_mk/plugin-api/

# REST API Documentation (ReDoc) — replace v1 with unstable for the unstable API
https://<server>/<site>/check_mk/api/v1/doc/

# REST API Interactive GUI (Swagger UI)
https://<server>/<site>/check_mk/api/v1/ui/
```

The old `api/1.0/` spelling still works but is legacy. Details on versions, authentication and the unstable endpoints: `rest_api.md`.

## Plugin Development File Locations

### Directory Structure
```
~/local/lib/python3/cmk_addons/plugins/<family>/
├── agent_based/        # Check plugins (Check API V2)
├── rulesets/           # Rules (Rulesets API V1)  
├── graphing/           # Metrics (Graphing API V1)
├── server_side_calls/  # Special agent configs
├── libexec/            # Special agent executables
├── checkman/           # Man pages
├── bakery/             # Bakery plugins (2.5+, cmk.bakery.v2_unstable)
└── inventory_ui/       # Inventory UI plugins (2.5+)
```

`bakery/` and `inventory_ui/` are new in 2.5; everything else is identical in 2.4. The symlinks `~/lib/check_mk` and `~/local/lib/check_mk` were removed in 2.5 (Werk #17969).

### Built-in Plugins (for reference)
```
~/lib/python3/cmk/plugins/          # Shipped plugins
~/lib/python3/cmk/plugins/collection/  # Main collection
```

### Agent Plugins (on monitored hosts)
```
/usr/lib/check_mk_agent/plugins/    # Linux
C:\ProgramData\checkmk\agent\plugins\  # Windows
```

## API Import Cheat Sheet

### Check API V2
```python
from cmk.agent_based.v2 import (
    # Sections
    AgentSection, SimpleSNMPSection, SNMPSection, SNMPTree,
    # Plugins
    CheckPlugin, InventoryPlugin,
    # Results
    Service, Result, State, Metric, HostLabel,
    # Utilities
    check_levels, render, get_value_store, GetRateError,
    # SNMP Detection
    startswith, endswith, contains, matches, exists, equals,
    not_startswith, not_endswith, not_contains, not_matches, not_exists,
    all_of, any_of,
    # Types
    StringTable, RuleSetType,
)
```

### Rulesets API V1
```python
from cmk.rulesets.v1 import Title, Label, Help

from cmk.rulesets.v1.form_specs import (
    # Containers
    Dictionary, DictElement, List,  # no Tuple in v1
    # Basic types
    String, Integer, Float, BooleanChoice,
    # Selection
    SingleChoice, SingleChoiceElement,
    CascadingSingleChoice, CascadingSingleChoiceElement,
    MultipleChoice, MultipleChoiceElement,
    # Special
    Password, migrate_to_password,
    SimpleLevels, Levels, LevelDirection,
    DefaultValue, InputHint,
    # Validators submodule: validators.NumberInRange, validators.LengthInRange, validators.MatchRegex, ...
    validators,
)

from cmk.rulesets.v1.rule_specs import (
    CheckParameters, DiscoveryParameters,
    HostCondition, HostAndItemCondition,
    Topic, SpecialAgent, ActiveCheck,
)
```

### Graphing API V1
```python
from cmk.graphing.v1 import Title

from cmk.graphing.v1.metrics import (
    Metric, Color, Unit,
    DecimalNotation, SINotation, IECNotation,
    StandardScientificNotation, EngineeringScientificNotation,
    TimeNotation,
)

from cmk.graphing.v1.graphs import Graph, MinimalRange

from cmk.graphing.v1.perfometers import (
    Perfometer, Bidirectional, Stacked,
    FocusRange, Closed, Open,
)

from cmk.graphing.v1.translations import (
    Translation, RenameTo, ScaleBy, RenameToAndScaleBy,
)
```

### Server-Side Calls API
```python
from cmk.server_side_calls.v1 import (
    noop_parser,
    SpecialAgentConfig, SpecialAgentCommand,
    ActiveCheckConfig, ActiveCheckCommand,
    HostConfig, Secret,
)
```

## Variable Naming Prefixes (CRITICAL)

Plugins are auto-discovered by name prefix:

| Prefix | Plugin Type | Example |
|--------|-------------|---------|
| `agent_section_` | Agent section | `agent_section_mycheck` |
| `snmp_section_` | SNMP section | `snmp_section_mydevice` |
| `check_plugin_` | Check plugin | `check_plugin_mycheck` |
| `inventory_plugin_` | Inventory plugin | `inventory_plugin_myinv` |
| `rule_spec_` | Ruleset spec | `rule_spec_mycheck` |
| `special_agent_` | Special agent config | `special_agent_myagent` |
| `active_check_` | Active check config | `active_check_myactive` |
| `metric_` | Metric definition | `metric_mymetric` |
| `graph_` | Graph definition | `graph_mygraph` |
| `perfometer_` | Perfometer | `perfometer_myperf` |
| `translation_` | Metric translation | `translation_legacy` |
| `bakery_plugin_` | Bakery plugin (2.5+, v2_unstable) | `bakery_plugin_myplugin` |
| `node_` | Inventory UI node (2.5+) | `node_myapp` |

## Development Workflow

### 1. Create Plugin Files
```bash
# Create family directory
mkdir -p ~/local/lib/python3/cmk_addons/plugins/mycompany/agent_based
mkdir -p ~/local/lib/python3/cmk_addons/plugins/mycompany/rulesets
mkdir -p ~/local/lib/python3/cmk_addons/plugins/mycompany/graphing
```

### 2. Write Plugin Code
```bash
vim ~/local/lib/python3/cmk_addons/plugins/mycompany/agent_based/mycheck.py
```

### 3. Test Syntax
```bash
python3 -m py_compile ~/local/lib/python3/cmk_addons/plugins/mycompany/agent_based/mycheck.py
```

### 4. Restart Services (if needed)
```bash
# For ruleset/graphing changes
omd restart apache

# For search index
omd restart redis
```

### 5. Test Discovery
```bash
cmk -vI --detect-plugins=mycheck hostname
```

### 6. Test Check Execution
```bash
cmk -v --detect-plugins=mycheck hostname
cmk --debug --detect-plugins=mycheck hostname  # With debug
```

### 7. Activate Changes
```bash
cmk -R
```

## External Resources

- **Checkmk Exchange** - https://exchange.checkmk.com - Community plugins with source code
- **GitHub Examples** - https://github.com/Checkmk/checkmk-docs/tree/master/examples
- **REST API Tutorial** - Checkmk YouTube channel
- **Knowledge Base** - https://kb.checkmk.com

## Livestatus Quick Reference

Query status data directly:

```bash
# From command line (as site user)
lq "GET hosts\nColumns: name state\nFilter: state != 0"

# Via Unix socket
echo -e "GET services\nColumns: host_name description state\nFilter: state = 2" | \
    unixcat ~/tmp/run/live
```

Common tables: `hosts`, `services`, `hostgroups`, `servicegroups`, `contacts`, `downtimes`, `comments`, `log`

## Local Checks (Simple Alternative)

For quick, simple checks without full plugin development:

```bash
#!/bin/bash
# /usr/lib/check_mk_agent/local/mycheck

# Output format: STATUS NAME METRICS SUMMARY
# STATUS: 0=OK, 1=WARN, 2=CRIT, 3=UNKNOWN

value=$(cat /proc/loadavg | cut -d' ' -f1)
echo "P \"Load Average\" load=$value;4;8 Current load: $value"
```

Output formats:
- `0 "Service Name" - Text` - Simple OK
- `1 "Service Name" - Warning text` - Simple WARN  
- `2 "Service Name" - Critical text` - Simple CRIT
- `P "Service Name" metric=value;warn;crit;min;max Text` - With metrics
