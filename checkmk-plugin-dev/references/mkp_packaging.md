# MKP Packaging Guide

MKP (Monitoring Kit Package) is the standard format for CheckMK extensions.

## CRITICAL: Package Management Safety

> **WARNING: `mkp disable` and `mkp remove` DELETE FILES!**
>
> When plugin files are bind-mounted from a development workspace (e.g., Docker volumes), these commands permanently delete source files!

### Safe Commands

| Command | Effect | Use When |
|---------|--------|----------|
| `mkp release <name>` | Unregisters package, **keeps files** | Detaching files without deletion |
| `mkp enable <name> <version>` | Restores from MKP archive | Recovering after accidental disable |
| `mkp package <manifest>` | Builds .mkp file | **Always build before disable/remove!** |

### Dangerous Commands

| Command | Effect | DANGER |
|---------|--------|--------|
| `mkp disable <name>` | Unregisters AND **DELETES all package files** | Destroys bind-mounted source! |
| `mkp remove <name> <version>` | **DELETES package and files permanently** | No recovery without backup! |

### Safe Workflow for Development

```bash
# 1. ALWAYS build MKP first (creates recoverable archive)
mkp package ~/var/check_mk/packages/myplugin

# 2. Now safe to disable (files can be restored from MKP)
mkp disable myplugin

# 3. To recover deleted files
mkp enable myplugin 1.0.0
```

### Recovery After Accidental Deletion

```bash
# If you built an MKP before deletion:
mkp enable <name> <version>

# If no MKP exists: restore from git/backup
git checkout -- local/lib/python3/cmk_addons/plugins/myplugin/
```

## Quick Start

```bash
# List all packages
mkp list

# Find unpackaged local files
mkp find

# Create manifest template for new package
mkp template myplugin

# Build .mkp from manifest
mkp package ~/var/check_mk/packages/myplugin

# Add external .mkp to site
mkp add myplugin-1.0.0.mkp

# Enable specific version
mkp enable myplugin 1.0.0
```

## Key File Locations

| Path | Purpose |
|------|---------|
| `~/var/check_mk/packages/<name>` | Active manifest for installed package |
| `~/var/check_mk/packages_local/<name>-<ver>.mkp` | Built .mkp files |
| `~/tmp/check_mk/<name>.manifest.temp` | Template output (new packages only) |
| `~/local/lib/python3/cmk_addons/plugins/<name>/` | Plugin source files |

## MKP CLI Commands

```bash
# List all packages (shows active version)
mkp list

# List all versions including inactive
mkp list --all

# Show files in a specific package version
mkp files <name> <version>

# Find unpackaged local files
mkp find

# Create manifest template (for NEW packages)
mkp template <name>

# Build .mkp from manifest path
mkp package <manifest_path>

# Add external .mkp file to site
mkp add <file.mkp>

# Enable specific version (makes it active)
mkp enable <name> <version>

# Disable package
mkp disable <name>

# Remove package AND delete files
mkp remove <name> <version>

# Remove package but KEEP files as unpackaged
mkp release <name>
```

## Directory Structure (CheckMK 2.4)

```
~/local/lib/python3/cmk_addons/plugins/<family>/
├── __init__.py                    # Optional, can be empty
├── agent_based/
│   ├── __init__.py
│   └── mycheck.py
├── checkman/
│   └── mycheck                    # Manual page (no extension!)
├── graphing/
│   ├── __init__.py
│   └── mymetrics.py
├── libexec/
│   └── agent_myagent              # Special agent (no extension!)
├── rulesets/
│   ├── __init__.py
│   └── mycheck.py
└── server_side_calls/
    ├── __init__.py
    └── special_agent.py
```

## Package Manifest Format

**IMPORTANT:** The manifest is a **Python literal**, not JSON! Use `None` not `null`.

```python
# ~/var/check_mk/packages/myplugin
{'author': 'Your Name',
 'description': 'Package description.\n\nMulti-line supported.',
 'download_url': 'https://github.com/you/myplugin',
 'files': {'cmk_addons_plugins': ['myplugin/agent_based/mycheck.py',
                                   'myplugin/libexec/agent_myplugin',
                                   'myplugin/rulesets/special_agent.py',
                                   'myplugin/server_side_calls/special_agent.py',
                                   'myplugin/graphing/metrics.py']},
 'name': 'myplugin',
 'title': 'My Plugin Title',
 'version': '1.0.0',
 'version.min_required': '2.4.0p1',
 'version.packaged': '2.4.0p14',
 'version.usable_until': None}
```

## File Categories in Manifest

| Key | Local Path |
|-----|------------|
| `cmk_addons_plugins` | `local/lib/python3/cmk_addons/plugins/<name>/` |
| `lib` | `local/lib/` |
| `agents` | `local/share/check_mk/agents/` |
| `web` | `local/share/check_mk/web/` |
| `checkman` | `local/share/check_mk/checkman/` |

### Including Checkman Files in MKP

Checkman files (man pages) are part of `cmk_addons_plugins` when using the new plugin structure:

```python
# In manifest 'files' section:
'files': {
    'cmk_addons_plugins': [
        'myplugin/agent_based/mycheck.py',
        'myplugin/checkman/mycheck',        # No file extension!
        'myplugin/rulesets/mycheck.py',
    ]
}
```

**Path format:** `<plugin_family>/checkman/<check_name>` (no extension)

The checkman file must match the check plugin name exactly.

## Workflows

### New Package

```bash
# 1. Create manifest template (finds all unpackaged files)
mkp template mypackage

# 2. Edit template - IMPORTANT: remove unwanted files, set metadata
vi ~/tmp/check_mk/mypackage.manifest.temp

# 3. Build .mkp from template
mkp package ~/tmp/check_mk/mypackage.manifest.temp

# 4. Add the built package to site
mkp add ~/var/check_mk/packages_local/mypackage-1.0.0.mkp

# 5. Enable the package
mkp enable mypackage 1.0.0
```

### Update Existing Package (simpler)

```bash
# 1. Make code changes to files in:
#    ~/local/lib/python3/cmk_addons/plugins/myplugin/

# 2. Edit manifest: bump version, add any new files
vi ~/var/check_mk/packages/myplugin

# 3. Package (auto-activates new version)
mkp package ~/var/check_mk/packages/myplugin

# 4. Copy .mkp for distribution
cp ~/var/check_mk/packages_local/myplugin-X.Y.Z.mkp /path/to/distribute/
```

## Version Management

Multiple versions can coexist:

```
$ mkp list
myplugin  1.0.2  Enabled (active on this site)
myplugin  1.0.1  Enabled (inactive on this site)
myplugin  1.0.0  Enabled (inactive on this site)
```

Only one version is "active" - the one whose files are deployed. Use `mkp enable <name> <version>` to switch.

## Common Pitfalls

### 1. `mkp template` includes too many files

`mkp template` finds ALL unpackaged files including pip packages and other unrelated files. **Always edit the manifest** to include only your plugin files.

```bash
# After running mkp template, edit the manifest:
vi ~/tmp/check_mk/mypackage.manifest.temp
# Remove unwanted files from the 'files' section
```

### 2. `mkp remove` deletes files!

Use `mkp release` if you want to keep files as unpackaged:

```bash
# DELETES files from local/
mkp remove myplugin 1.0.0

# Keeps files, just removes package registration
mkp release myplugin
```

### 3. Manual tar doesn't work

Don't manually create .mkp files with tar. Use `mkp package` which handles the correct format (gzipped tar with Python literal manifest).

### 4. Version already exists

Can't `mkp add` if same version already exists. Either remove first or increment version:

```bash
# Option 1: Remove existing version first
mkp remove myplugin 1.0.0
mkp add myplugin-1.0.0.mkp

# Option 2: Increment version in manifest before building
```

### 5. Editing existing manifest auto-activates

When you `mkp package` an existing package's manifest (in `~/var/check_mk/packages/`), the new version becomes active automatically.

## Checkman Pages (Manual)

Create documentation for your checks:

```
# ~/local/lib/python3/cmk_addons/plugins/myplugin/checkman/mycheck
title: My Check
agents: linux, windows
catalog: os/services
license: GPLv2
distribution: check_mk
description:
 This check monitors something important.

 It creates one service per item found and
 monitors the status.

 Thresholds can be configured via WATO rules.

item:
 The name of the monitored item.

discovery:
 One service is created for each item found.
```

### Checkman Fields

| Field | Description |
|-------|-------------|
| `title` | Short title for the integration |
| `agents` | Supported agents: linux, windows, snmp, etc. |
| `catalog` | Category for sorting (os/services, hw/network, etc.) |
| `license` | License (GPLv2, MIT, etc.) |
| `distribution` | Distribution type |
| `description` | Detailed description |
| `item` | What the item represents |
| `discovery` | How discovery works |

## Versioning Best Practices

```python
# Semantic Versioning: MAJOR.MINOR.PATCH
'version': '1.0.0'   # Initial release
'version': '1.0.1'   # Bug fix
'version': '1.1.0'   # New feature
'version': '2.0.0'   # Breaking change

# CheckMK version compatibility
'version.packaged': '2.4.0p16'     # Version used for packaging
'version.min_required': '2.4.0p1'  # Minimum required version
'version.usable_until': None       # Use None, not null (Python literal!)
```

## Development with Git

Recommended repository structure:

```
myplugin/
├── .github/
│   └── workflows/
│       └── build.yml           # CI/CD for MKP build
├── local/
│   └── lib/
│       └── python3/
│           └── cmk_addons/
│               └── plugins/
│                   └── myplugin/
│                       ├── agent_based/
│                       ├── checkman/
│                       ├── graphing/
│                       ├── libexec/
│                       ├── rulesets/
│                       └── server_side_calls/
├── package                      # MKP manifest
├── README.md
├── LICENSE
└── Makefile
```

### Makefile Example

```makefile
NAME := myplugin
VERSION := $(shell grep "'version':" package | cut -d"'" -f4)

.PHONY: build clean install

build:
	mkp package package
	mv ~/var/check_mk/packages_local/$(NAME)-$(VERSION).mkp .

install:
	mkp add $(NAME)-$(VERSION).mkp
	mkp enable $(NAME) $(VERSION)

clean:
	rm -f $(NAME)-*.mkp

test:
	python3 -m pytest tests/
```

### GitHub Actions Workflow

```yaml
# .github/workflows/build.yml
name: Build MKP

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    container:
      image: checkmk/check-mk-raw:2.4.0-latest

    steps:
      - uses: actions/checkout@v4

      - name: Copy plugin files
        run: |
          cp -r local/lib/python3/cmk_addons/plugins/* \
            /omd/sites/cmk/local/lib/python3/cmk_addons/plugins/
          cp package /omd/sites/cmk/var/check_mk/packages/myplugin

      - name: Build MKP
        run: |
          su - cmk -c "mkp package /omd/sites/cmk/var/check_mk/packages/myplugin"

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: mkp
          path: /omd/sites/cmk/var/check_mk/packages_local/*.mkp
```

## Troubleshooting

### Package fails to install

```bash
# Check version conflict - same version may already exist
mkp list --all

# Remove existing version first if needed
mkp remove myplugin 1.0.0

# Then add
mkp add myplugin-1.0.0.mkp
```

### Files not found

```bash
# Check file groups in manifest
mkp files myplugin 1.0.0

# Check actual files exist
ls -la ~/local/lib/python3/cmk_addons/plugins/myplugin/
```

### Import errors after installation

```bash
# Check Python path
python3 -c "import cmk.agent_based.v2; print('OK')"

# Restart Apache (for web/ruleset changes)
omd restart apache

# Reload core (for check changes)
cmk -R
```

### Rule not visible after installation

```bash
# Check for syntax errors in ruleset
tail -f ~/var/log/web.log

# Restart Apache
omd restart apache
```

## Migration from Legacy Packages

Old packages (Check API v1) can exist in parallel but should be migrated:

```bash
# Identify old files
ls ~/local/share/check_mk/checks/        # Old (v1)
ls ~/local/lib/python3/cmk_addons/plugins/  # New (v2)

# Perform migration
# 1. Port check from v1 to v2 API
# 2. Move files to new structure
# 3. Release old package (keeps files for reference)
mkp release oldplugin

# 4. Or remove completely
mkp remove oldplugin 1.0.0
```
