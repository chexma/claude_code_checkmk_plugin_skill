---
name: checkmk-plugin-dev
description: >
  This skill should be used when the user develops CheckMK 2.4 or 2.5
  extensions: agent-based and SNMP checks, special agents, active checks,
  agent and local plugins, rulesets, graphing, HW/SW inventory, Agent
  Bakery plugins, MKP packages, legacy plugin migration, or Python/shell
  clients for the CheckMK REST API (v1 and 2.5 unstable). Trigger phrases:
  "create a CheckMK plugin", "write an SNMP check", "build a special
  agent", "add metrics or a perfometer", "create a ruleset", "write a
  bakery plugin", "package an MKP", "write a local check", "script the
  CheckMK REST API", or mentions of cmk_addons, cmk.agent_based.v2 or
  cmk.server_side_calls. Do NOT use for manual GUI/Setup configuration,
  site administration, or generic Nagios/Linux monitoring questions.
compatibility: Requires CheckMK 2.4+ environment. Claude Code recommended.
metadata:
  author: andre
  version: 2.0.0
---

# CheckMK Plugin Development (2.4 & 2.5)

Comprehensive guidance for developing CheckMK monitoring plugins using current APIs.

## Which CheckMK Version?

The core APIs (Check API V2, Rulesets API V1, Graphing API V1, Server-Side Calls V1) are **identical** in 2.4 and 2.5 — nearly all reference files and templates below work unchanged for either version. Only ask about the target version when the task touches one of these:

| Area | Stable (2.4 and 2.5) | 2.5+ only (unstable) |
|---|---|---|
| Agent Bakery | `references/bakery_api.md` → Version 1 (`cmk.base.plugins.bakery.bakery_api.v1`) | `references/bakery_api.md` → Version 2 (`cmk.bakery.v2_unstable`) |
| Reading stored secrets in server-side programs | — (use `Password` form spec + `.unsafe()`) | `references/password_store_api.md` (`v1_unstable`) |
| Crash reports / call-to-call persistence for special agents | — | `references/server_side_programs_api.md` (`v1_unstable`) |
| Custom HW/SW inventory tree visualizations | — | `references/inventory_ui_api.md` (`v1_unstable`) |
| Custom DCD connector (commercial editions) | — | `references/dcd_connector_api.md` (unversioned) |
| Automating CheckMK via REST API (dashboards, availability, relays, OTel, …) | `references/rest_api.md` → `v1` | `references/rest_api.md` → `unstable` endpoints |

### Stability and timeline

This is the one place for the timeline. Reference files only link here.

- All `*_unstable` APIs above are **unstable** in 2.5 and may change incompatibly.
- They are planned to become stable (renamed) in the **next major release, 3.0.0**. Werk #19370 corrects Werk #18600 here: there is no 2.6/2.7.
- The legacy APIs they replace (bakery API v1, `cmk.special_agents.v0_unstable`, `cmk.utils.password_store`) are **deprecated in 3.0.0 and removed in 3.1.0**.
- REST API endpoints under `/api/unstable/` may change or disappear at any time.

**Tell the user before recommending any unstable API for production use.** This also applies to the special-agent and active-check templates, which use one by default:

- The executables (`datasource_complete.py`, `active_check_executable.py`) use `cmk.password_store.v1_unstable` on 2.5 and fall back to a plain `--password` on 2.4.
- The server-side-call templates (`datasource_server_side_calls.py`, `active_check_server_side_calls.py`) emit `--password-id` by default, which works on 2.5 only. For 2.4, switch to the commented `.unsafe()` line.

Say this when you hand the templates over.

## Choose Your Path

| To accomplish... | Start here | Template |
|---|---|---|
| Monitor a REST API (cloud, app) | `references/special_agents.md` | `datasource_complete.py` |
| Monitor network devices (SNMP) | `references/snmp_api.md` | `snmp_check.py` |
| Process agent output | `references/agent_based_api.md` | `agent_check_simple.py` |
| Check network services (HTTP/TCP) | `references/active_checks.md` | `active_check_executable.py` |
| Run scripts on monitored hosts | `references/agent_plugins.md` | `linux_agent_plugin.py` |
| Create simplest host-side check | `references/local_checks.md` | `local_check.py` |
| Feed data from cron jobs/external programs | `references/spool_directory.md` | - |
| Monitor VMs/containers | `references/piggyback_api.md` | `datasource_complete.py` |
| Distribute plugins via Agent Bakery | `references/bakery_api.md` | `bakery_plugin.py` (v1) / `bakery_plugin_v2.py` (2.5 unstable) |
| Package for distribution | `references/mkp_packaging.md` | - |
| Migrate existing Nagios plugin | `references/migration_guide.md` | - |
| Script CheckMK itself (REST API client) | `references/rest_api.md` | - |

## Core APIs

Shared by 2.4 and 2.5 (unchanged):

| API | Import | Purpose |
|-----|--------|---------|
| Check API V2 | `cmk.agent_based.v2` | Agent-based and SNMP checks |
| Rulesets API V1 | `cmk.rulesets.v1` | Rule configuration forms |
| Graphing API V1 | `cmk.graphing.v1` | Metrics, graphs, perfometers |
| Server-Side Calls | `cmk.server_side_calls.v1` | Special agents and active checks |

Version-specific:

| API | Import | Version | Purpose |
|-----|--------|---------|---------|
| Bakery API v1 | `cmk.base.plugins.bakery.bakery_api.v1` | 2.3+ (stable, also 2.5) | Agent Bakery distribution |
| Bakery API v2 | `cmk.bakery.v2_unstable` | 2.5+ (unstable) | Agent Bakery distribution, new layout |
| Password Store | `cmk.password_store.v1_unstable` | 2.5+ (unstable) | Read stored secrets in server-side programs |
| Server-Side Programs | `cmk.server_side_programs.v1_unstable` | 2.5+ (unstable) | Crash reports, call-to-call persistence |
| Inventory UI | `cmk.inventory_ui.v1_unstable` | 2.5+ (unstable) | Custom HW/SW inventory visualizations |

## Directory Structure

Place all plugins under `~/local/lib/python3/cmk_addons/plugins/<family_name>/`:

```
<family_name>/
├── agent_based/       # Check plugins (agent & SNMP)
├── rulesets/          # Rule definitions
├── graphing/          # Metrics, graphs, perfometers
├── server_side_calls/ # Special agent configs
├── libexec/           # Special agent executables
├── checkman/          # Man pages
├── bakery/            # Bakery plugins (2.5+, cmk.bakery.v2_unstable)
└── inventory_ui/      # Inventory UI views (2.5+, cmk.inventory_ui.v1_unstable)
```

Exception: **Bakery API v1** plugins (stable, 2.4 and 2.5) do *not* go into `cmk_addons`. They live in `~/local/lib/python3/cmk/base/cee/plugins/bakery/`. Only v2_unstable plugins use `<family>/bakery/`.

Since 2.5 the symlinks `~/lib/check_mk` and `~/local/lib/check_mk` are gone (Werk #17969). Always use the real paths below `~/local/lib/python3/`.

## Variable Naming (CRITICAL)

Plugins are discovered by variable name prefix:

| Prefix | Type |
|--------|------|
| `agent_section_` | Agent sections |
| `snmp_section_` | SNMP sections |
| `check_plugin_` | Check plugins |
| `inventory_plugin_` | Inventory plugins |
| `rule_spec_` | Ruleset specifications |
| `metric_`, `graph_`, `perfometer_`, `translation_` | Graphing elements |
| `special_agent_`, `active_check_` | Server-side calls |
| `bakery_plugin_` | Bakery plugins (2.5+, v2_unstable) |
| `node_` | Inventory UI nodes (2.5+) |

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
- `references/bakery_api.md` - Agent Bakery distribution (v1 stable + v2_unstable for 2.5)
- `references/active_checks.md` - Network service checks
- `references/agent_plugins.md` - Host-side scripts
- `references/local_checks.md` - Simplest host-side checks
- `references/spool_directory.md` - Agent spool directory for output of cron jobs and external programs
- `references/inventory_api.md` - HW/SW inventory collection (agent_based side)
- `references/inventory_ui_api.md` - **2.5+ unstable**: custom inventory tree visualizations
- `references/password_store_api.md` - **2.5+ unstable**: reading stored secrets
- `references/server_side_programs_api.md` - **2.5+ unstable**: crash reports, persistence helpers
- `references/host_labels.md` - Auto-assign labels
- `references/mkp_packaging.md` - Package distribution
- `references/migration_guide.md` - Legacy plugin migration
- `references/best_practices.md` - Testing, debugging, crash analysis
- `references/checkman_manpages.md` - Man page format
- `references/rest_api.md` - CheckMK REST API client: v1 vs **unstable** (2.5), auth, new endpoints
- `references/dcd_connector_api.md` - **2.5, commercial**: Dynamic Configuration Daemon connectors

## Templates

Ready-to-use templates. All template file names in this skill are relative to `assets/templates/`.

### First Plugin
1. `agent_check_simple.py` → 2. `ruleset.py` → 3. `graphing.py`

Next step: `agent_check_advanced.py` (items, check parameters, metrics)

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
1. `bakery_plugin.py` (v1, stable, 2.3–2.4+) or `bakery_plugin_v2.py` (v2_unstable, 2.5+) → 2. `bakery_ruleset.py`

## Common Patterns

### Render Functions
```python
render.percent(50.5)      # "50.50%"
render.bytes(1024)        # "1.00 KiB"
render.timespan(3661)     # "1 hour 1 minute"
render.datetime(ts)       # "2024-01-01 12:00:00"
```

### State Evaluation
```python
yield Result(state=State.OK, summary="Status text")
yield Result(state=State.WARN, summary="Warning", details="Extended info")
```

## Troubleshooting

See `references/best_practices.md` for debugging, crash analysis, and common errors.

Quick fixes:
- **Plugin not discovered**: Check variable naming prefixes (see Variable Naming above)
- **Check that all plugins load**: `cmk-validate-plugins` (add `-d` to raise the first exception)
- **TypeError in check function**: Verify `check_levels()` format (see check_levels() Format above)
- **Ruleset not visible**: Run `omd restart apache` after changes
- **Import errors**: Ensure correct API version imports (`cmk.agent_based.v2`, not `.v1`)

## In-CheckMK Documentation

Access via **Help > Developer resources** for Sphinx API docs, REST API ReDoc, and Swagger UI. REST API docs: `/check_mk/api/v1/doc/` (stable) and `/check_mk/api/unstable/doc/` (unstable) — see `references/rest_api.md`.
