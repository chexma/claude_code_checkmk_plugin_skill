# CheckMK Plugin Development Skill for Claude Code

A comprehensive Claude Code skill for developing CheckMK 2.4 monitoring plugins. This skill provides detailed API documentation, ready-to-use templates, and best practices for all CheckMK extension types.

## What This Skill Does

When activated, this skill enables Claude Code to:

- Create agent-based check plugins using Check API V2
- Develop SNMP monitoring plugins with proper OID detection
- Build special agents for REST API integration
- Implement active checks for network service monitoring
- Write local checks and agent plugins
- Define rulesets, metrics, graphs, and perfometers
- Package extensions as MKP files

## Installation

### Claude Code

```bash
# Add the skill to Claude Code
claude skill add /path/to/checkmk-plugin-dev.skill
```

### Manual Setup

Copy the `checkmk-plugin-dev/` directory to your Claude Code skills location.

## Skill Contents

### Reference Documentation (16 files)

| File | Description |
|------|-------------|
| `development_overview.md` | Decision tree for choosing extension type |
| `api_overview.md` | Complete API ecosystem and imports |
| `agent_based_api.md` | Check API V2 for agent-based plugins |
| `snmp_api.md` | SNMP detection and OID handling |
| `rulesets_api.md` | Form specs and rule definitions |
| `graphing_api.md` | Metrics, graphs, perfometers |
| `special_agents.md` | REST API integration (Datasource Programs) |
| `active_checks.md` | Server-side network service checks |
| `piggyback_api.md` | Multi-host monitoring |
| `inventory_api.md` | HW/SW inventory collection |
| `agent_plugins.md` | Host-side scripts with server evaluation |
| `local_checks.md` | Simplest host-side scripts |
| `spool_directory.md` | External program output |
| `bakery_api.md` | Agent Bakery distribution |
| `mkp_packaging.md` | Extension packaging |
| `best_practices.md` | Testing, debugging, migration |

### Templates (17 files)

**Basic Plugins**
- `agent_check_simple.py` - Minimal agent-based check
- `agent_check_advanced.py` - Check with items, params, metrics
- `snmp_check.py` - 5 SNMP examples (scalar, table, metrics, rates, detection)
- `snmp_check_multitable.py` - Multi-table SNMP with dataclasses
- `ruleset.py` - Ruleset definition
- `graphing.py` - Metrics and perfometer definitions
- `special_agent.py` - Basic special agent executable

**Complete Datasource Program**
- `datasource_complete.py` - Full special agent with piggyback
- `datasource_server_side_calls.py` - Server-side call configuration
- `datasource_ruleset.py` - Complete ruleset with check parameters

**Agent Plugins**
- `linux_agent_plugin.py` - Python plugin with config, sections, piggyback
- `linux_agent_plugin.sh` - Bash plugin with config support
- `windows_agent_plugin.ps1` - PowerShell plugin with WMI, registry

**Local Checks**
- `local_check.py` - Cross-platform Python template
- `local_check_linux.sh` - Bash template
- `local_check_windows.ps1` - PowerShell template

**Bakery & Active Checks**
- `bakery_plugin.py` - Bakery plugin with scriptlets
- `bakery_ruleset.py` - AgentConfig ruleset
- `active_check_executable.py` - Nagios-compatible executable
- `active_check_server_side_calls.py` - ActiveCheckConfig
- `active_check_ruleset.py` - ActiveCheck ruleset

## CheckMK 2.4 Plugin Structure

```
~/local/lib/python3/cmk_addons/plugins/<family_name>/
├── agent_based/        # Check plugins (agent & SNMP)
├── rulesets/           # Rule definitions
├── graphing/           # Metrics, graphs, perfometers
├── server_side_calls/  # Special agent configs
├── libexec/            # Special agent executables
└── checkman/           # Man pages
```

## Quick Example

```python
from cmk.agent_based.v2 import (
    AgentSection, CheckPlugin, Service, Result, State, check_levels, render
)

def parse_mycheck(string_table):
    return {line[0]: {"value": float(line[1])} for line in string_table}

def discover_mycheck(section):
    for item in section:
        yield Service(item=item)

def check_mycheck(item, params, section):
    data = section.get(item)
    if not data:
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

## Core APIs

| API | Module | Purpose |
|-----|--------|---------|
| Check API V2 | `cmk.agent_based.v2` | Agent-based and SNMP checks |
| Rulesets API V1 | `cmk.rulesets.v1` | Rule configuration forms |
| Graphing API V1 | `cmk.graphing.v1` | Metrics and visualization |
| Server-Side Calls | `cmk.server_side_calls.v1` | Special agents and active checks |

## Variable Naming (Critical)

Plugins are auto-discovered by prefix:

| Prefix | Type |
|--------|------|
| `agent_section_` | Agent sections |
| `snmp_section_` | SNMP sections |
| `check_plugin_` | Check plugins |
| `rule_spec_` | Ruleset specifications |
| `metric_` | Metric definitions |
| `graph_` | Graph definitions |
| `perfometer_` | Perfometer definitions |
| `special_agent_` | Special agent configs |
| `active_check_` | Active check configs |

## Testing

```bash
# Syntax check
python3 -m py_compile plugin.py

# Service discovery
cmk -vI --detect-plugins=myplugin hostname

# Execute check
cmk -v --detect-plugins=myplugin hostname

# Debug mode
cmk --debug --detect-plugins=myplugin hostname

# Restart services
omd restart apache  # For ruleset/graphing changes
cmk -R              # For core/check changes
```

## Resources

- [CheckMK Exchange](https://exchange.checkmk.com) - Community plugins
- [CheckMK Documentation](https://docs.checkmk.com) - Official docs
- In-CheckMK: **Help > Developer resources** for API references

## License

This skill is provided for use with Claude Code.
