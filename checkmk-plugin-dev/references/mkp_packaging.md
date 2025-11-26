# MKP Packaging Guide

MKP (Monitoring Kit Package) ist das Standardformat für CheckMK-Erweiterungen.

## Schnellstart

```bash
# MKPs auflisten
mkp list

# Neues Paket erstellen
mkp template myplugin

# Paket bauen
mkp package myplugin

# Paket installieren
mkp install myplugin-1.0.0.mkp

# Paket deinstallieren
mkp uninstall myplugin
```

## Verzeichnisstruktur (CheckMK 2.4)

```
~/local/lib/python3/cmk_addons/plugins/<family>/
├── __init__.py                    # Optional, kann leer sein
├── agent_based/
│   ├── __init__.py
│   └── mycheck.py
├── checkman/
│   └── mycheck                    # Manual page (ohne Extension!)
├── graphing/
│   ├── __init__.py
│   └── mymetrics.py
├── libexec/
│   └── agent_myagent              # Special Agent (ohne Extension!)
├── rulesets/
│   ├── __init__.py
│   └── mycheck.py
└── server_side_calls/
    ├── __init__.py
    └── special_agent.py
```

## Package Manifest

Die `package` Datei im MKP definiert Metadaten:

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

## mkp CLI Befehle

```bash
# Alle MKP-Befehle
mkp --help

# Installierte Pakete anzeigen
mkp list

# Paket-Details
mkp show myplugin

# Dateien eines Pakets anzeigen
mkp files myplugin

# Vorlage erstellen (interaktiv)
mkp template myplugin

# Paket erstellen aus Manifest
mkp package myplugin

# Paket installieren
mkp install myplugin-1.0.0.mkp

# Paket deinstallieren (Dateien bleiben in local/)
mkp uninstall myplugin

# Paket und Dateien entfernen
mkp remove myplugin

# Aktivierte vs. deaktivierte Pakete
mkp list --all

# Paket deaktivieren (bleibt installiert)
mkp disable myplugin

# Paket aktivieren
mkp enable myplugin
```

## Dateigruppen in MKP

| Gruppe | Pfad | Beschreibung |
|--------|------|--------------|
| `cmk_addons_plugins` | `lib/python3/cmk_addons/plugins/<family>/` | Hauptplugin-Code |
| `agent_based` | `share/check_mk/agents/plugins/` | Agent-Plugins (laufen auf Hosts) |
| `agents` | `share/check_mk/agents/` | Agent-Dateien |
| `checkman` | `share/check_mk/checkman/` | Manual Pages (legacy) |
| `checks` | `share/check_mk/checks/` | Check API v1 (legacy) |
| `doc` | `share/doc/check_mk/` | Dokumentation |
| `lib` | `lib/` | Zusätzliche Libraries |
| `notifications` | `share/check_mk/notifications/` | Notification Plugins |
| `pnp-templates` | `share/check_mk/pnp-templates/` | PNP4Nagios Templates |
| `web` | `share/check_mk/web/` | Web UI Erweiterungen |

## Workflow: Plugin zu MKP

### 1. Plugin entwickeln und testen

```bash
# Entwicklung in local/
cd ~/local/lib/python3/cmk_addons/plugins/

# Plugin-Familie erstellen
mkdir -p myplugin/{agent_based,rulesets,graphing,checkman}

# Code entwickeln und testen
cmk -vI --detect-plugins=mycheck testhost
cmk -v --detect-plugins=mycheck testhost
```

### 2. Manifest erstellen

```bash
# Interaktiv
mkp template myplugin

# Oder manuell
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

### 3. Paket bauen

```bash
mkp package myplugin
# Erzeugt: ~/var/check_mk/packages_local/myplugin-1.0.0.mkp
```

### 4. Verteilen

- Upload im Web: Setup > Extension Packages
- Kopieren auf andere Server
- Publish auf CheckMK Exchange

## Checkman Pages (Manual)

Erstelle Dokumentation für deine Checks:

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

### Checkman Felder

| Feld | Beschreibung |
|------|--------------|
| `title` | Kurzer Titel für die Integration |
| `agents` | Unterstützte Agenten: linux, windows, snmp, etc. |
| `catalog` | Kategorie für Sortierung (os/services, hw/network, etc.) |
| `license` | Lizenz (GPLv2, MIT, etc.) |
| `distribution` | Verteilungsart |
| `description` | Ausführliche Beschreibung |
| `item` | Was das Item repräsentiert |
| `discovery` | Wie Discovery funktioniert |

## Versioning Best Practices

```python
# Semantic Versioning: MAJOR.MINOR.PATCH
"version": "1.0.0"   # Initial release
"version": "1.0.1"   # Bug fix
"version": "1.1.0"   # New feature
"version": "2.0.0"   # Breaking change

# CheckMK Versionskompatibilität
"version.packaged": "2.4.0p16"    # Version womit gepackt wurde
"version.min_required": "2.3.0"    # Mindestens erforderliche Version
```

## Entwicklung mit Git

Empfohlene Repository-Struktur:

```
myplugin/
├── .github/
│   └── workflows/
│       └── build.yml           # CI/CD für MKP-Build
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
├── package                      # MKP Manifest
├── README.md
├── LICENSE
└── Makefile
```

### Makefile Beispiel

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

### Paket lässt sich nicht installieren

```bash
# Fehlerdetails anzeigen
mkp install myplugin-1.0.0.mkp --verbose

# Versionskonflikt prüfen
cmk --version
# vs.
grep version.min_required package
```

### Dateien werden nicht gefunden

```bash
# Prüfe Dateigruppen im Manifest
mkp files myplugin

# Prüfe tatsächliche Dateien
ls -la ~/local/lib/python3/cmk_addons/plugins/myplugin/
```

### Import-Fehler nach Installation

```bash
# Python-Pfad prüfen
python3 -c "import cmk.agent_based.v2; print('OK')"

# Apache neu starten (für Web-Änderungen)
omd restart apache

# Core neu laden (für Check-Änderungen)
cmk -R
```

## Migration von Legacy-Paketen

Alte Pakete (Check API v1) können parallel existieren, sollten aber migriert werden:

```bash
# Alte Dateien identifizieren
ls ~/local/share/check_mk/checks/        # Alt (v1)
ls ~/local/lib/python3/cmk_addons/plugins/  # Neu (v2)

# Migration durchführen
# 1. Check von v1 nach v2 API portieren
# 2. Dateien in neue Struktur verschieben
# 3. Altes Paket entfernen
mkp remove oldplugin
```
