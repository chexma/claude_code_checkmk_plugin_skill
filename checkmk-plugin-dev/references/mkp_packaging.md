# MKP Packaging Guide

MKP (Monitoring Kit Package) is the standard format for CheckMK extensions.

## Quick Start

```bash
# List MKPs
mkp list

# Create new package
mkp template myplugin

# Build package
mkp package myplugin

# Install package
mkp install myplugin-1.0.0.mkp

# Uninstall package
mkp uninstall myplugin
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

## Package Manifest

The `package` file in the MKP defines metadata:

```python
# ~/var/check_mk/packages/myplugin
{
    "name": "myplugin",
    "title": "My Awesome Plugin",
    "description": "Monitors awesome things.",
    "version": "1.0.0",
    "version.packaged": "2.4.0p16",
    "version.min_required": "2.3.0",
    "author": "Your Name",
    "download_url": "https://github.com/you/myplugin",
    "files": {
        "cmk_addons_plugins": [
            "myplugin/agent_based/mycheck.py",
            "myplugin/rulesets/mycheck.py",
            "myplugin/graphing/mymetrics.py",
            "myplugin/checkman/mycheck",
        ],
    }
}
```

## mkp CLI Commands

```bash
# All MKP commands
mkp --help

# Show installed packages
mkp list

# Package details
mkp show myplugin

# Show files of a package
mkp files myplugin

# Create template (interactive)
mkp template myplugin

# Create package from manifest
mkp package myplugin

# Install package
mkp install myplugin-1.0.0.mkp

# Uninstall package (files remain in local/)
mkp uninstall myplugin

# Remove package and files
mkp remove myplugin

# Enabled vs. disabled packages
mkp list --all

# Disable package (stays installed)
mkp disable myplugin

# Enable package
mkp enable myplugin
```

## File Groups in MKP

| Group | Path | Description |
|-------|------|-------------|
| `cmk_addons_plugins` | `lib/python3/cmk_addons/plugins/<family>/` | Main plugin code |
| `agent_based` | `share/check_mk/agents/plugins/` | Agent plugins (run on hosts) |
| `agents` | `share/check_mk/agents/` | Agent files |
| `checkman` | `share/check_mk/checkman/` | Manual pages (legacy) |
| `checks` | `share/check_mk/checks/` | Check API v1 (legacy) |
| `doc` | `share/doc/check_mk/` | Documentation |
| `lib` | `lib/` | Additional libraries |
| `notifications` | `share/check_mk/notifications/` | Notification plugins |
| `pnp-templates` | `share/check_mk/pnp-templates/` | PNP4Nagios templates |
| `web` | `share/check_mk/web/` | Web UI extensions |

## Workflow: Plugin to MKP

### 1. Develop and Test Plugin

```bash
# Development in local/
cd ~/local/lib/python3/cmk_addons/plugins/

# Create plugin family
mkdir -p myplugin/{agent_based,rulesets,graphing,checkman}

# Develop and test code
cmk -vI --detect-plugins=mycheck testhost
cmk -v --detect-plugins=mycheck testhost
```

### 2. Create Manifest

```bash
# Interactive
mkp template myplugin

# Or manually
cat > ~/var/check_mk/packages/myplugin << 'EOF'
{
    "name": "myplugin",
    "title": "My Plugin",
    "description": "Description here",
    "version": "1.0.0",
    "version.packaged": "2.4.0p16",
    "version.min_required": "2.3.0",
    "author": "Your Name",
    "download_url": "",
    "files": {
        "cmk_addons_plugins": [
            "myplugin/agent_based/mycheck.py",
            "myplugin/rulesets/mycheck.py"
        ]
    }
}
EOF
```

### 3. Build Package

```bash
mkp package myplugin
# Creates: ~/var/check_mk/packages_local/myplugin-1.0.0.mkp
```

### 4. Distribute

- Upload in web: Setup > Extension Packages
- Copy to other servers
- Publish on CheckMK Exchange

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
"version": "1.0.0"   # Initial release
"version": "1.0.1"   # Bug fix
"version": "1.1.0"   # New feature
"version": "2.0.0"   # Breaking change

# CheckMK version compatibility
"version.packaged": "2.4.0p16"    # Version used for packaging
"version.min_required": "2.3.0"    # Minimum required version
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
VERSION := $(shell grep '"version":' package | cut -d'"' -f4)

.PHONY: build clean install

build:
	mkp package $(NAME)
	mv ~/var/check_mk/packages_local/$(NAME)-$(VERSION).mkp .

install:
	mkp install $(NAME)-$(VERSION).mkp

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
          su - cmk -c "mkp package myplugin"

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: mkp
          path: /omd/sites/cmk/var/check_mk/packages_local/*.mkp
```

## Troubleshooting

### Package fails to install

```bash
# Show error details
mkp install myplugin-1.0.0.mkp --verbose

# Check version conflict
cmk --version
# vs.
grep version.min_required package
```

### Files not found

```bash
# Check file groups in manifest
mkp files myplugin

# Check actual files
ls -la ~/local/lib/python3/cmk_addons/plugins/myplugin/
```

### Import errors after installation

```bash
# Check Python path
python3 -c "import cmk.agent_based.v2; print('OK')"

# Restart Apache (for web changes)
omd restart apache

# Reload core (for check changes)
cmk -R
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
# 3. Remove old package
mkp remove oldplugin
```
