# CheckMK Man Pages - Developer Reference

## Overview

Man pages provide documentation for check plugins that is accessible via the CheckMK command line and web interface. They describe what a check does, how it determines states, and how services are discovered.

## Location

Man pages are stored in the plugin directory under `checkman/`:

```
~/local/lib/python3/cmk_addons/plugins/<family_name>/checkman/
```

The filename must match the check plugin name (without file extension).

## File Format

Man pages are text files without a file extension using this format:

```
title: <Display Title>
agents: <agent_type>
catalog: <category/subcategory>
license: <License>
distribution: <Author/Distribution>
description:
 <Description text - EVERY line must start with a space>

item:
 <Item description - only for checks with %s in service name>

discovery:
 <Discovery description>
```

## Required Fields

| Field | Description | Examples |
|-------|-------------|----------|
| `title` | Display name | `MyPlugin: Component Name` |
| `agents` | Agent type | `snmp`, `linux`, `special_agent_name` |
| `catalog` | Category path | `storage/vendor`, `os/linux`, `virtual/vmware` |
| `license` | License type | `GPLv2`, `GPLv3`, `MIT` |
| `distribution` | Source | `check_mk` or author name |
| `description` | Multi-line description | Each line indented with space |
| `discovery` | Discovery behavior | How services are created |

## Optional Fields

| Field | When Required | Description |
|-------|---------------|-------------|
| `item` | Service name contains `%s` | Describes what the item represents |

## Formatting in Description

- `{text}` → displayed as **bold** or `monospace`
- Typical usage: `{CRIT}`, `{WARN}`, `{OK}` for states
- Empty lines create paragraphs
- No HTML/Markdown (displayed on CLI)

## Common Catalog Categories

| Category | Use For |
|----------|---------|
| `os/linux` | Linux-specific checks |
| `os/windows` | Windows-specific checks |
| `storage/vendor` | Storage vendor checks (e.g., `storage/netapp`) |
| `networking/vendor` | Network device checks |
| `virtual/vmware` | VMware checks |
| `virtual/proxmox` | Proxmox checks |
| `cloud/aws` | AWS checks |
| `cloud/azure` | Azure checks |
| `app/vendor` | Application-specific checks |
| `hw/server/vendor` | Hardware server checks |

## Complete Example

```
title: MyVendor Storage: Volumes
agents: myvendor_rest
catalog: storage/myvendor
license: GPLv2
distribution: author_name
description:
 This check monitors storage volumes on MyVendor storage systems.

 The check returns {CRIT} if the volume is offline,
 {WARN} for degraded states, and {OK} if the volume is healthy.

 Performance data includes capacity, used space, and IOPS.

 Requires the special agent "MyVendor Storage via REST API".

item:
 The volume name as reported by the storage system.

discovery:
 One service is created per volume found on the storage system.
```

## Example Without Item

For checks without items (single service per host):

```
title: MyVendor Storage: System Health
agents: myvendor_rest
catalog: storage/myvendor
license: GPLv2
distribution: author_name
description:
 This check monitors the overall health of MyVendor storage systems.

 Returns {CRIT} if any critical component has failed,
 {WARN} if components are degraded, {OK} otherwise.

discovery:
 One service is created per host.
```

## Testing Man Pages

### Display Man Page
```bash
cmk -M <check_plugin_name>
```

### Example Output
```bash
cmk -M myvendor_volumes
```

Shows the formatted man page content in the terminal.

### Verify All Man Pages
```bash
cmk -M  # Lists all available man pages
```

## Best Practices

1. **Match plugin name**: Filename must exactly match the `name` in `check_plugin_`
2. **Indent all content lines**: Every line under `description:`, `item:`, `discovery:` must start with a space
3. **Use state markers**: Reference `{OK}`, `{WARN}`, `{CRIT}`, `{UNKNOWN}` to describe conditions
4. **Document thresholds**: Explain what triggers each state
5. **Mention requirements**: Note if special agents or configurations are needed
6. **Be concise**: Man pages are reference documentation, not tutorials

## Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| Missing leading space | Content not recognized | Indent all content lines |
| File extension added | File not found | Remove `.txt` or other extensions |
| Wrong filename | Man page not linked | Use exact check plugin name |
| HTML/Markdown | Renders as plain text | Use `{text}` for emphasis |

## Integration with MKP Packaging

Man pages are automatically included when packaging with `mkp`:

```bash
mkp pack <family_name>
```

The `checkman/` directory contents are bundled in the MKP file.
