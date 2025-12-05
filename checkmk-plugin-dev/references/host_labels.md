# CheckMK Host Labels - Developer Reference

## Overview

Host labels enable automatic classification of hosts based on data collected by Special Agents or Check Plugins. Labels are detected during service discovery and assigned to the host.

## API

**Import:**
```python
from cmk.agent_based.v2 import AgentSection, HostLabel
```

**Class:** `HostLabel(name: str, value: str)`
- `name`: Label key (e.g., `"my_plugin/version"`)
- `value`: Label value (e.g., `"1.0"`)

## Implementation Patterns

### 1. Define Host Label Function

```python
def host_label_my_plugin(section):
    """Generate host labels from section data.

    Args:
        section: Parsed section data (dict from parse_function)

    Yields:
        HostLabel: One or more host labels
    """
    # Section can contain multiple items - for host labels
    # typically only process the first/single item
    for item_name, data in section.items():
        # Boolean label to identify the plugin type
        yield HostLabel("my_plugin", "true")

        # Data-based labels
        if version := data.get("Version"):
            yield HostLabel("my_plugin/version", version)

        if vendor := data.get("Vendor"):
            yield HostLabel("my_plugin/vendor", vendor)

        # Only process first entry (1 host = 1 device)
        break
```

### 2. Register AgentSection

```python
agent_section_my_plugin = AgentSection(
    name="my_plugin_section",
    parse_function=parse_my_plugin,
    parsed_section_name="my_plugin_section",
    host_label_function=host_label_my_plugin,  # Host label function
)
```

### 3. Complete Example

```python
#!/usr/bin/env python3
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    Result,
    State,
    Service,
    HostLabel,
)

def parse_my_plugin(string_table):
    """Parse JSON data from special agent."""
    import json
    parsed = {}
    for line in string_table:
        entry = json.loads(line[0])
        name = entry.get("Name", entry.get("Id"))
        parsed[name] = entry
    return parsed

def host_label_my_plugin(section):
    """Generate host labels for monitored devices."""
    for item_name, data in section.items():
        # Identification label
        yield HostLabel("my_plugin", "true")

        # Version
        if version := data.get("ProductVersion"):
            yield HostLabel("my_plugin/version", version)

        # Only first item
        break

def discover_my_plugin(section):
    for item in section:
        yield Service(item=item)

def check_my_plugin(item, section):
    if data := section.get(item):
        yield Result(state=State.OK, summary="Running")

# Registrations
agent_section_my_plugin = AgentSection(
    name="my_plugin_section",
    parse_function=parse_my_plugin,
    host_label_function=host_label_my_plugin,
)

check_plugin_my_plugin = CheckPlugin(
    name="my_plugin",
    service_name="My Plugin %s",
    sections=["my_plugin_section"],
    discovery_function=discover_my_plugin,
    check_function=check_my_plugin,
)
```

## Label Naming Conventions

### Format
```
prefix/key: value
```

### Recommended Structure
| Type | Format | Example |
|------|--------|---------|
| Identification | `{plugin}` | `netapp:true` |
| Version | `{plugin}/version` | `netapp/version:9.12` |
| Type/Model | `{plugin}/model` | `netapp/model:AFF-A400` |
| Vendor | `{plugin}/vendor` | `storage/vendor:NetApp` |
| Feature | `{plugin}/{feature}` | `netapp/ha:enabled` |

### Best Practices
- **Use prefix**: Prefix all labels with plugin-specific namespace
- **Lowercase**: Use lowercase for keys
- **No special characters**: Only alphanumeric, `/`, `-`, `_`
- **No spaces**: Avoid spaces in keys and values
- **Short values**: Labels are for filtering, not descriptions

## Testing

### Discovery with Label Output
```bash
cmk -vvII --detect-plugins=my_plugin hostname
```

### Expected Output
```
+ ANALYSE DISCOVERED HOST LABELS
Trying host label discovery with: my_plugin_section
  my_plugin: true (my_plugin_section)
  my_plugin/version: 1.0.0 (my_plugin_section)
SUCCESS - Found 2 host labels
```

### Activate Labels
```bash
cmk -vII hostname    # Run discovery
cmk -O               # Activate configuration
```

## Common Use Cases

### 1. Device Type Identification
```python
yield HostLabel("storage/type", "san")
yield HostLabel("storage/vendor", "datacore")
```

### 2. Feature Flags
```python
if data.get("HasReplication"):
    yield HostLabel("my_plugin/replication", "enabled")
```

### 3. Environment Classification
```python
if "prod" in data.get("Environment", "").lower():
    yield HostLabel("my_plugin/env", "production")
```

### 4. Hardware Properties
```python
if data.get("IsVirtualMachine"):
    yield HostLabel("my_plugin/virtualized", "true")
```

## Usage in CheckMK

### Filtering in Rules
Labels can be used as conditions in CheckMK rules:
- Setup → Hosts → Host Rules → Conditions → Host Labels

### Example Filters
```
my_plugin:true                    # All hosts with this plugin
my_plugin/version:~10\..*         # Version 10.x (regex)
my_plugin/env:production          # Production environment
```

### Filtering in Views
- Monitor → Hosts → Filter → Host Labels

## Important Notes

1. **Parse function must exist**: `host_label_function` receives output from `parse_function`
2. **No access to params**: Host label function has no access to ruleset parameters
3. **Only during discovery**: Labels are only detected during `cmk -II`
4. **Idempotency**: Function should yield the same labels for the same input
5. **Performance**: Function is called on every discovery - keep it lean
