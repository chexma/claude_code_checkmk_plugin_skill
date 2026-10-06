# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Repository Purpose

Claude Code skill for CheckMK plugin development, covering **both 2.4 and 2.5**. Provides documentation and templates for creating monitoring plugins.

## Version Policy (2.4 vs 2.5)

The core plugin APIs (`cmk.agent_based.v2`, `cmk.rulesets.v1`, `cmk.graphing.v1`, `cmk.server_side_calls.v1`) are **identical** between CheckMK 2.4 and 2.5 — most reference files apply to both versions without changes.

Three areas differ and are explicitly version-tagged:

1. **Bakery API** (`references/bakery_api.md`) has two versions living side by side:
   - `cmk.base.plugins.bakery.bakery_api.v1` — stable, use for CheckMK 2.3–2.4 and for 2.5 unless you need the new features.
   - `cmk.bakery.v2_unstable` — CheckMK 2.5+, new plugin family layout, `BakeryPlugin` class instead of `register.bakery_plugin()`, `Secret` objects instead of raw password-store access. Marked unstable until it stabilizes in 3.0.0.
2. **Four brand-new 2.5-only APIs** with no 2.4 equivalent — each has its own reference file, clearly marked "2.5+, unstable":
   - `references/password_store_api.md` — `cmk.password_store.v1_unstable`
   - `references/server_side_programs_api.md` — `cmk.server_side_programs.v1_unstable`
   - `references/inventory_ui_api.md` — `cmk.inventory_ui.v1_unstable`
   - `references/dcd_connector_api.md` — `cmk.nonfree.pro.dcd.connector_api` (commercial editions, unversioned)
3. **REST API** (`references/rest_api.md`): `/api/v1/` is stable; `/api/unstable/` is a superset with 50 extra 2.5 endpoints that may change without notice. Not a plugin API — client-side automation only.

Migration timeline per Werk #18600, corrected by Werk #19370 (2.5.0p11 — the next major is 3.0.0, there is no 2.6/2.7): unstable in 2.5 → stabilized (renamed) in 3.0.0 → legacy APIs (bakery v1, `cmk.special_agents.v0_unstable`, `cmk.utils.password_store`) deprecated in 3.0.0 and removed in 3.1.0. When writing new plugin code, ask which CheckMK version the user targets before choosing between stable v1 and unstable v2/new APIs — see `SKILL.md`'s version note.

## Structure

```
.claude-plugin/
├── marketplace.json      # Self-hosted marketplace "chexma-checkmk" (lists this repo as plugin)
└── plugin.json           # Plugin manifest; "skills" points at ./checkmk-plugin-dev
checkmk-plugin-dev/
├── SKILL.md              # Main skill entry point
├── references/           # Detailed API documentation (24 files)
└── assets/templates/     # Ready-to-use plugin templates (21 files)
```

## Distribution (Plugin Marketplace)

The repo is both a plain skill (copy `checkmk-plugin-dev/`) and a self-hosted
Claude Code plugin marketplace on GitHub (not the official Anthropic directory).
Users install it with:

```bash
claude plugin marketplace add chexma/claude_code_checkmk_plugin_skill
claude plugin install checkmk-plugin-dev@chexma-checkmk
```

Fixed decisions — do not change without a strong reason:

- **Keep `checkmk-plugin-dev/` at the repo root.** Don't move it to `skills/`.
  `plugin.json` points at it via `"skills": ["./checkmk-plugin-dev"]`, and
  manual copies and existing clone scripts depend on that path.
- **Marketplace name `chexma-checkmk`, plugin ID `checkmk-plugin-dev@chexma-checkmk`.**
  Renaming forces every user to re-add the marketplace and breaks
  `enabledPlugins` entries in project `.claude/settings.json` files (e.g. the
  CheckMK devcontainer template, which installs the plugin this way).
- **No email addresses in `plugin.json` / `marketplace.json`.** Name only.
- **No `.skill` ZIP bundle.** The old `checkmk-plugin-dev.skill` was removed;
  the plugin and the plain folder copy are the only install paths.

## Releasing

Installed plugins are tracked by `version` in `.claude-plugin/plugin.json`.
If it stays the same, `claude plugin update` finds nothing new — so bump it
with **every** commit that should reach users (content changes in
`checkmk-plugin-dev/` included; repo-only changes like this file don't need it).
Releases are tagged from 1.0.1 on (1.0.0 is intentionally untagged).

```bash
git pull --ff-only                          # repo is edited from several machines/devcontainers
# 1. bump "version" in .claude-plugin/plugin.json (semver: patch for doc fixes)
claude plugin validate .                    # expect "passed with warnings" (see below)
claude --plugin-dir . plugin details checkmk-plugin-dev   # must list "Skills (1) checkmk-plugin-dev"
# 2. commit + push
claude plugin tag --push .                  # creates + pushes tag checkmk-plugin-dev--v<version>
```

The only expected `validate` warning is "CLAUDE.md at the plugin root is not
loaded as project context". That's fine: this file is guidance for working on
the repo, not plugin content.

To verify a release reached users, on any machine with the plugin installed:

```bash
claude plugin marketplace update chexma-checkmk
claude plugin update checkmk-plugin-dev@chexma-checkmk   # "updated from X to Y"
claude plugin list                                        # shows new version
```

Then restart Claude Code to load the new version.

## Key Files

- **SKILL.md**: Entry point with decision tree, quick start, and references
- **references/agent_based_api.md**: Check API V2, check_levels format, TypedDict patterns
- **references/rulesets_api.md**: Form specs, factory functions
- **references/graphing_api.md**: Metrics, graphs, perfometers
- **references/bakery_api.md**: Bakery v1 (stable) vs v2_unstable (2.5+) side by side
- **references/special_agents.md**: Special agents, incl. the SSL gotcha: on OMD sites `REQUESTS_CA_BUNDLE` overrides `session.verify=False` unless `verify=` is passed per request; test with `requests_mock`, not a `MagicMock` session
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
cmk-validate-plugins                           # Check all plugins load
cmk -D hostname                                # Effective params
omd restart apache                             # After ruleset changes
```
