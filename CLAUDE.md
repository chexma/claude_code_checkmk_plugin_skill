# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Repository Purpose

Claude Code skill for CheckMK plugin development, covering **both 2.4 and 2.5**. Provides documentation and templates for creating monitoring plugins.

## Version Policy (2.4 vs 2.5)

The core plugin APIs (`cmk.agent_based.v2`, `cmk.rulesets.v1`, `cmk.graphing.v1`, `cmk.server_side_calls.v1`) are **identical** between CheckMK 2.4 and 2.5 — most reference files apply to both versions without changes.

Three areas differ and are explicitly version-tagged:

1. **Bakery API** (`references/bakery_api.md`) has two versions living side by side:
   - `cmk.base.plugins.bakery.bakery_api.v1` — stable, use for CheckMK 2.3–2.4 and for 2.5 unless you need the new features.
   - `cmk.bakery.v2_unstable` — CheckMK 2.5+, new plugin family layout, `BakeryPlugin` class instead of `register.bakery_plugin()`, `Secret` objects instead of raw password-store access. Marked unstable until it stabilizes in 2.6.
2. **Three brand-new 2.5-only unstable APIs** with no 2.4 equivalent — each has its own reference file, clearly marked "2.5+, unstable":
   - `references/password_store_api.md` — `cmk.password_store.v1_unstable`
   - `references/server_side_programs_api.md` — `cmk.server_side_programs.v1_unstable`
   - `references/inventory_ui_api.md` — `cmk.inventory_ui.v1_unstable`
3. **REST API** (`references/rest_api.md`): `/api/v1/` is stable; `/api/unstable/` is a superset with 50 extra 2.5 endpoints that may change without notice. Not a plugin API — client-side automation only.

Migration timeline per Werk #18600: unstable in 2.5 → stabilized (renamed) in 2.6 → legacy APIs removed in 2.7. When writing new plugin code, ask which CheckMK version the user targets before choosing between stable v1 and unstable v2/new APIs — see `SKILL.md`'s version note.

## Structure

```
checkmk-plugin-dev/
├── SKILL.md              # Main skill entry point
├── references/           # Detailed API documentation (23 files)
└── assets/templates/     # Ready-to-use plugin templates (22 files)
```

## Key Files

- **SKILL.md**: Entry point with decision tree, quick start, and references
- **references/agent_based_api.md**: Check API V2, check_levels format, TypedDict patterns
- **references/rulesets_api.md**: Form specs, factory functions
- **references/graphing_api.md**: Metrics, graphs, perfometers
- **references/bakery_api.md**: Bakery v1 (stable) vs v2_unstable (2.5+) side by side
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
