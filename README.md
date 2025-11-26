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

Copy or git clone the `checkmk-plugin-dev/` directory to your Claude Code skills location.

Personal skills in:
~/.claude/skills/

​Project skills in the projects folder:
.claude/skills/my-skill-name


## Skill Contents

### Reference Documentation (17 files)

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
| `migration_guide.md` | Migrating legacy plugins to current APIs |
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

## License

This skill is provided for use with Claude Code.
