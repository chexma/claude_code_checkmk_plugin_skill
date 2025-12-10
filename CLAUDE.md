# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a Claude Code skill for CheckMK 2.4 plugin development. It provides comprehensive documentation and templates for creating monitoring plugins using CheckMK's APIs.

## Structure

```
checkmk-plugin-dev/
├── SKILL.md              # Main skill entry point with quick reference
├── references/           # Detailed API documentation (17 markdown files)
└── assets/templates/     # Ready-to-use plugin templates (17 Python files)
```

The `checkmk-plugin-dev.skill` file in the root is the bundled skill file.

## Key Files

- **SKILL.md**: Start here. Contains API overview, directory structure, naming conventions, and links to detailed references
- **references/development_overview.md**: Decision tree for choosing extension type
- **references/agent_based_api.md**: Check API V2 details
- **references/rulesets_api.md**: Form specs and rule definitions
- **references/graphing_api.md**: Metrics, graphs, perfometers
- **references/migration_guide.md**: Migrating legacy plugins to current APIs (with helper scripts)

## CheckMK 2.4 Plugin Directory Structure

All plugins go under `~/local/lib/python3/cmk_addons/plugins/<family_name>/`:
- `agent_based/` - Check plugins (agent & SNMP)
- `rulesets/` - Rule definitions
- `graphing/` - Metrics, graphs, perfometers
- `server_side_calls/` - Special agent configs
- `libexec/` - Special agent executables

## Critical Naming Convention

Plugins are discovered by variable name prefix:
- `agent_section_` - Agent sections
- `snmp_section_` - SNMP sections
- `check_plugin_` - Check plugins
- `rule_spec_` - Ruleset specifications
- `metric_`, `graph_`, `perfometer_` - Graphing elements
- `special_agent_`, `active_check_` - Server-side calls

## Core APIs

| API | Import | Purpose |
|-----|--------|---------|
| Check API V2 | `cmk.agent_based.v2` | Agent-based and SNMP checks |
| Rulesets API V1 | `cmk.rulesets.v1` | Rule configuration forms |
| Graphing API V1 | `cmk.graphing.v1` | Metrics and visualization |
| Server-Side Calls | `cmk.server_side_calls.v1` | Special agents and active checks |

## Testing Commands

```bash
# Service discovery
cmk -vI --detect-plugins=myplugin hostname

# Execute check
cmk -v --detect-plugins=myplugin hostname

# Debug mode
cmk --debug --detect-plugins=myplugin hostname

# Show effective parameters per service
cmk -D hostname

# Restart after ruleset/graphing changes
omd restart apache
```

## Critical: check_levels() Format (v2 API)

```python
# CORRECT formats:
levels_upper=("fixed", (warn, crit))    # Fixed thresholds
levels_upper=("no_levels", None)        # Explicitly disabled
levels_upper=None                       # No levels

# WRONG - causes TypeError!
levels_upper=(warn, crit)               # Missing level type!
```

SimpleLevels from Rulesets API produces the correct format - pass directly to check_levels().

## Key Documentation Updates

- **references/agent_based_api.md**: Critical check_levels v2 format warning, TypedDict patterns for parameters
- **references/rulesets_api.md**: Factory functions for DRY ruleset definitions
- **references/best_practices.md**: Crash report analysis commands
- **references/mkp_packaging.md**: Checkman file inclusion in MKP manifest
