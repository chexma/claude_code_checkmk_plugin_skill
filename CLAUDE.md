# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Repository Purpose

Claude Code skill for CheckMK 2.4 plugin development. Provides documentation and templates for creating monitoring plugins.

## Structure

```
checkmk-plugin-dev/
├── SKILL.md              # Main skill entry point
├── references/           # Detailed API documentation (17 files)
└── assets/templates/     # Ready-to-use plugin templates (17 files)
```

## Key Files

- **SKILL.md**: Entry point with decision tree, quick start, and references
- **references/agent_based_api.md**: Check API V2, check_levels format, TypedDict patterns
- **references/rulesets_api.md**: Form specs, factory functions
- **references/graphing_api.md**: Metrics, graphs, perfometers
- **references/best_practices.md**: Testing, debugging, crash analysis

## Plugin Directory Structure

All plugins under `~/local/lib/python3/cmk_addons/plugins/<family_name>/`:
- `agent_based/` - Check plugins
- `rulesets/` - Rule definitions
- `graphing/` - Metrics, graphs, perfometers
- `server_side_calls/` - Special agent configs
- `libexec/` - Special agent executables

## Variable Naming Prefixes (CRITICAL)

| Prefix | Type |
|--------|------|
| `agent_section_` | Agent sections |
| `snmp_section_` | SNMP sections |
| `check_plugin_` | Check plugins |
| `rule_spec_` | Ruleset specifications |
| `metric_`, `graph_`, `perfometer_` | Graphing elements |

## check_levels() Format (CRITICAL)

```python
# CORRECT:
levels_upper=("fixed", (warn, crit))
levels_upper=("no_levels", None)
levels_upper=None

# WRONG - TypeError:
levels_upper=(warn, crit)
```

## Testing Commands

```bash
cmk -vI --detect-plugins=myplugin hostname    # Discovery
cmk -v --detect-plugins=myplugin hostname     # Execute
cmk --debug --detect-plugins=myplugin hostname # Debug
cmk -D hostname                                # Effective params
omd restart apache                             # After ruleset changes
```
