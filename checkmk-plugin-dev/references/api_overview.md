# CheckMK API Ecosystem Overview

## Available APIs in CheckMK 2.4

| API | Purpose | Location |
|-----|---------|----------|
| **REST API** | Full automation (hosts, rules, services, downtimes) | Help > Developer resources > REST API |
| **Check API V2** | Agent-based & SNMP check plugins | `cmk.agent_based.v2` |
| **Rulesets API V1** | Rule configuration forms | `cmk.rulesets.v1` |
| **Graphing API V1** | Metrics, graphs, perfometers | `cmk.graphing.v1` |
| **Server-side Calls API** | Special agents & active checks | `cmk.server_side_calls.v1` |
| **Bakery API** | Agent bakery integration | `cmk.base.cee.plugins.bakery` |
| **HW/SW Inventory API** | Hardware/Software inventory | Web API |
| **Livestatus** | Real-time status queries | Unix socket / TCP |
| **Local Checks** | Simple script-based checks | Agent output format |

## In-Checkmk Resources

Access via **Help > Developer resources**:

- **Plug-in API references** - Sphinx documentation for all plugin APIs
- **REST API documentation** - ReDoc/OpenAPI reference with code examples
- **REST API interactive GUI** - Swagger UI for testing endpoints

## API Documentation URLs (in CheckMK)

```
# Plugin API Reference (internal)
https://<server>/<site>/check_mk/plugin-api/

# REST API Documentation
https://<server>/<site>/check_mk/api/1.0/ui/

# REST API Interactive GUI  
https://<server>/<site>/check_mk/api/1.0/ui/swagger-ui/
```

## Plugin Development File Locations

### CheckMK 2.4 Directory Structure
```
~/local/lib/python3/cmk_addons/plugins/<family>/
├── agent_based/        # Check plugins (Check API V2)
├── rulesets/           # Rules (Rulesets API V1)  
├── graphing/           # Metrics (Graphing API V1)
├── server_side_calls/  # Special agent configs
├── libexec/            # Special agent executables
├── checkman/           # Man pages
└── inventory_ui/       # Inventory UI plugins
```

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
    Dictionary, DictElement, List, Tuple,
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
    # Validators
    NumberInRange, LengthInRange, MatchRegex,
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
