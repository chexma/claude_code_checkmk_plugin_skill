# CheckMK Plugin Development Skill for Claude Code

A comprehensive Claude Code skill for developing CheckMK monitoring plugins for **both 2.4 and 2.5**. This skill provides detailed API documentation, ready-to-use templates, and best practices for all CheckMK extension types. The core APIs are identical across 2.4 and 2.5; the Bakery API and three new 2.5-only unstable APIs (password store, server-side programs, inventory UI) are explicitly version-tagged — see `checkmk-plugin-dev/SKILL.md`'s version note.

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

### As a Claude Code plugin (recommended)

This repository is also a self-hosted Claude Code plugin marketplace. Add it
once and install the plugin:

```bash
claude plugin marketplace add chexma/claude_code_checkmk_plugin_skill
claude plugin install checkmk-plugin-dev@chexma-checkmk
```

Or inside a Claude Code session: `/plugin marketplace add chexma/claude_code_checkmk_plugin_skill`,
then pick `checkmk-plugin-dev` in `/plugin`.

Update to the latest version with:

```bash
claude plugin marketplace update chexma-checkmk
claude plugin update checkmk-plugin-dev@chexma-checkmk
```

To get updates automatically, enable auto-update for the `chexma-checkmk`
marketplace in `/plugin` (it is off by default for third-party marketplaces).

To preinstall it for everyone working on a project (e.g. in a devcontainer
template), add this to the project's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "chexma-checkmk": {
      "source": { "source": "github", "repo": "chexma/claude_code_checkmk_plugin_skill" }
    }
  },
  "enabledPlugins": {
    "checkmk-plugin-dev@chexma-checkmk": true
  }
}
```

### As a plain skill

Copy or git clone the `checkmk-plugin-dev/` directory to your Claude Code skills location.

Personal skills in:
~/.claude/skills/

​Project skills in the projects folder:
.claude/skills/my-skill-name


## Skill Contents

### Reference Documentation (24 files)

| File | Description |
|------|-------------|
| `development_overview.md` | Decision tree for choosing extension type |
| `api_overview.md` | Complete API ecosystem and imports (2.4 & 2.5) |
| `agent_based_api.md` | Check API V2 for agent-based plugins |
| `snmp_api.md` | SNMP detection and OID handling |
| `rulesets_api.md` | Form specs and rule definitions |
| `graphing_api.md` | Metrics, graphs, perfometers |
| `special_agents.md` | REST API integration (Datasource Programs) |
| `active_checks.md` | Server-side network service checks |
| `piggyback_api.md` | Multi-host monitoring |
| `inventory_api.md` | HW/SW inventory collection |
| `inventory_ui_api.md` | **2.5+ unstable**: custom inventory tree visualizations |
| `agent_plugins.md` | Host-side scripts with server evaluation |
| `local_checks.md` | Simplest host-side scripts |
| `spool_directory.md` | External program output |
| `bakery_api.md` | Agent Bakery distribution (v1 stable + v2_unstable for 2.5) |
| `password_store_api.md` | **2.5+ unstable**: reading stored secrets |
| `server_side_programs_api.md` | **2.5+ unstable**: crash reports, persistence helpers |
| `mkp_packaging.md` | Extension packaging |
| `migration_guide.md` | Migrating legacy plugins to current APIs |
| `best_practices.md` | Testing, debugging, migration |
| `dcd_connector_api.md` | **2.5, commercial**: Dynamic Configuration Daemon connectors |
| `rest_api.md` | CheckMK REST API client: v1 (stable) and unstable (2.5+) endpoints |

### Templates (21 files)

**Basic Plugins**
- `agent_check_simple.py` - Minimal agent-based check
- `agent_check_advanced.py` - Check with items, params, metrics
- `snmp_check.py` - 5 SNMP examples (scalar, table, metrics, rates, detection)
- `snmp_check_multitable.py` - Multi-table SNMP with dataclasses
- `ruleset.py` - Ruleset definition
- `graphing.py` - Metrics and perfometer definitions

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
- `bakery_plugin.py` - Bakery plugin with scriptlets (v1, stable, 2.3+ incl. 2.5)
- `bakery_plugin_v2.py` - Bakery plugin, v2_unstable (CheckMK 2.5+)
- `bakery_ruleset.py` - AgentConfig ruleset
- `active_check_executable.py` - Nagios-compatible executable
- `active_check_server_side_calls.py` - ActiveCheckConfig
- `active_check_ruleset.py` - ActiveCheck ruleset

## License

This skill is provided for use with Claude Code.
