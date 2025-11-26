# Local Checks

Local Checks are the simplest way to create custom services in CheckMK. The status is determined directly in the script - no check plugin on the server required.

## Difference from Agent Plugins

| Type | Status Calculation | Server-side Code | Complexity |
|------|-------------------|------------------|------------|
| **Local Check** | In script on host | Not required | Simple |
| **Agent Plugin** | Check plugin on server | Required | Medium |

## Directories

| Operating System | Path |
|-----------------|------|
| Linux/Unix | `/usr/lib/check_mk_agent/local/` |
| Windows | `C:\ProgramData\checkmk\agent\local\` |

## Output Format

Each line creates one service:

```
<STATUS> "<SERVICE_NAME>" <METRIC> <STATUS_TEXT>
```

| Field | Description | Example |
|-------|-------------|---------|
| STATUS | `0`=OK, `1`=WARN, `2`=CRIT, `3`=UNKNOWN, `P`=dynamic | `0` |
| SERVICE_NAME | Name in double quotes | `"My Service"` |
| METRIC | Metric definition or `-` for none | `count=42;30;50` |
| STATUS_TEXT | Any text (may contain spaces) | `Everything OK` |

## Simple Examples

### Bash (Linux)

```bash
#!/bin/bash
# /usr/lib/check_mk_agent/local/my_check

# Static OK status
echo '0 "My Service" - Everything is fine'

# Status based on condition
if systemctl is-active --quiet myapp; then
    echo '0 "MyApp Status" - Service is running'
else
    echo '2 "MyApp Status" - Service is NOT running!'
fi
```

### PowerShell (Windows)

```powershell
# C:\ProgramData\checkmk\agent\local\my_check.ps1

# Static check
Write-Host '0 "My Windows Service" - All good'

# Service check
$svc = Get-Service -Name "MyApp" -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -eq "Running") {
    Write-Host '0 "MyApp Service" - Running'
} else {
    Write-Host '2 "MyApp Service" - Not running!'
}
```

### Python (Cross-platform)

```python
#!/usr/bin/env python3
# /usr/lib/check_mk_agent/local/my_check

import shutil

def check_disk_space(path, warn_percent=80, crit_percent=90):
    """Check disk space and output local check format."""
    try:
        total, used, free = shutil.disk_usage(path)
        used_percent = (used / total) * 100
        
        # Determine status
        if used_percent >= crit_percent:
            status = 2
        elif used_percent >= warn_percent:
            status = 1
        else:
            status = 0
        
        # Output local check format with metric for graphing
        print(f'{status} "Disk {path}" used={used_percent:.1f};{warn_percent};{crit_percent} '
              f'Used: {used_percent:.1f}% of {total // (1024**3)} GB')
    
    except Exception as e:
        print(f'3 "Disk {path}" - Error: {e}')

check_disk_space("/")
check_disk_space("/var")
```

## Metrics

### Basic Syntax

```
metricname=value
```

### Full Syntax

```
metricname=value;warn;crit;min;max
```

### Examples

```bash
# Value only
echo '0 "Queue Size" count=42 Queue has 42 items'

# With thresholds (dynamic state calculation)
echo 'P "CPU Usage" cpu=73;80;90 CPU at 73%'

# With min/max for graph scaling
echo 'P "Memory" memory=85;80;90;0;100 Memory at 85%'

# Multiple metrics (separated by |)
echo '0 "Network" in=1024|out=512 Traffic stats'

# On Windows: escape pipe with ^
echo 0 "Network" in=1024^|out=512 Traffic stats
```

## Dynamic State Calculation (P)

Using `P` instead of a number lets CheckMK calculate the state from thresholds:

```bash
#!/bin/bash
# State is computed from threshold values

TEMP=$(cat /sys/class/thermal/thermal_zone0/temp)
TEMP_C=$((TEMP / 1000))

# P = dynamic: WARN at 70°C, CRIT at 85°C
echo "P \"CPU Temperature\" temperature=${TEMP_C};70;85 CPU: ${TEMP_C}°C"
```

**Output examples:**
- `temperature=65` → OK (below 70)
- `temperature=75` → WARN (between 70 and 85)
- `temperature=90` → CRIT (above 85)

## Lower and Upper Thresholds

For values that should stay within a range (e.g., humidity):

```
metricname=value;warn_lower:warn_upper;crit_lower:crit_upper
```

```bash
# Humidity should be between 30-70%
# WARN if <40 or >60, CRIT if <30 or >70
echo "P \"Humidity\" humidity=45;40:60;30:70 Humidity: 45%"

# Lower thresholds only
echo "P \"Battery\" battery=25;30:;20: Battery at 25%"
```

## Multi-line Output

For details below the summary:

```bash
#!/bin/bash
# Use \n for line breaks

DETAILS="Line 1\nLine 2\nLine 3"
echo "0 \"My Service\" - Summary text\n${DETAILS}"
```

## Asynchronous Execution (Caching)

For scripts with long execution time:

### Linux

Move to subdirectory named with seconds interval:

```bash
# Execute every 10 minutes (600 seconds)
mkdir -p /usr/lib/check_mk_agent/local/600/
mv /usr/lib/check_mk_agent/local/slow_check /usr/lib/check_mk_agent/local/600/
```

### Windows

Configure in `check_mk.user.yml`:

```yaml
local:
  enabled: yes
  execution:
    - pattern: $CUSTOM_LOCAL_PATH$\slow_check.ps1
      async: yes
      cache_age: 600
```

## Complete Example: Backup Check

```bash
#!/bin/bash
# /usr/lib/check_mk_agent/local/600/backup_check
# Runs every 10 minutes (in 600/ directory)

BACKUP_DIR="/var/backups"
MAX_AGE_HOURS=25
WARN_SIZE_MB=100
CRIT_SIZE_MB=10

# Find newest backup file
LATEST=$(find "$BACKUP_DIR" -name "*.tar.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1)

if [[ -z "$LATEST" ]]; then
    echo '2 "Backup Status" - No backup files found!'
    exit 0
fi

# Get age and size
BACKUP_FILE=$(echo "$LATEST" | cut -d' ' -f2-)
BACKUP_TIME=$(stat -c %Y "$BACKUP_FILE")
CURRENT_TIME=$(date +%s)
AGE_HOURS=$(( (CURRENT_TIME - BACKUP_TIME) / 3600 ))
SIZE_MB=$(( $(stat -c %s "$BACKUP_FILE") / 1024 / 1024 ))

# Determine status
if [[ $AGE_HOURS -gt $MAX_AGE_HOURS ]]; then
    STATUS=2
    MSG="Backup is ${AGE_HOURS}h old (max: ${MAX_AGE_HOURS}h)!"
elif [[ $SIZE_MB -lt $CRIT_SIZE_MB ]]; then
    STATUS=2
    MSG="Backup too small: ${SIZE_MB}MB"
elif [[ $SIZE_MB -lt $WARN_SIZE_MB ]]; then
    STATUS=1
    MSG="Backup smaller than expected: ${SIZE_MB}MB"
else
    STATUS=0
    MSG="Last backup: ${AGE_HOURS}h ago, Size: ${SIZE_MB}MB"
fi

# Output with metrics
echo "${STATUS} \"Backup Status\" age=${AGE_HOURS};24;48|size=${SIZE_MB};${WARN_SIZE_MB}:;${CRIT_SIZE_MB}: ${MSG}"
```

## Distribution via Agent Bakery (Enterprise)

1. Create directory:
```bash
mkdir -p ~/local/share/check_mk/agents/custom/mypackage/lib/local/
```

2. Place script there

3. In Setup > Agents > Agent rules > Deploy custom files with agent select the package

## Using Known Metrics

Use existing metric names for automatic units and Perf-O-Meters:

| Metric | Unit | Example |
|--------|------|---------|
| `temperature` | °C | `temperature=42;50;60` |
| `humidity` | % | `humidity=55;40:60;30:70` |
| `if_in_octets` | Bytes/s | `if_in_octets=1048576` |
| `mem_used_percent` | % | `mem_used_percent=75;80;90` |
| `cpu_utilization` | % | `cpu_utilization=45;80;90` |

See `~/lib/python3/cmk/plugins/collection/graphing/` for all available metrics.

## Debugging

### Test Script Directly

```bash
# Linux
chmod +x /usr/lib/check_mk_agent/local/my_check
/usr/lib/check_mk_agent/local/my_check

# Windows PowerShell
& "C:\ProgramData\checkmk\agent\local\my_check.ps1"
```

### Check Agent Output

```bash
# Linux
cmk-agent-ctl dump | grep -A5 "<<<local"

# Windows
./cmk-agent-ctl.exe dump | Select-String -Pattern "<<<local" -Context 0,5
```

### Test on CheckMK Server

```bash
# Service Discovery
cmk -IIv --detect-plugins=local myhost

# Execute check
cmk -nv --detect-plugins=local myhost
```

## Common Errors

1. **Script not executable** (Linux)
   ```bash
   chmod +x /usr/lib/check_mk_agent/local/my_check
   ```

2. **Wrong quotes**
   - Service name must be in double quotes
   - In Bash: `echo '0 "My Service" - OK'` or `echo "0 \"My Service\" - OK"`

3. **Special characters in service name**
   - Not allowed: `; ' !`
   - Better: letters, numbers, spaces, hyphens

4. **Windows: UTF-16 instead of UTF-8**
   ```powershell
   # At the beginning of the script:
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   ```

5. **No line breaks in output** (except masked with `\n`)

## Best Practices

1. **Short execution time**: Scripts should be fast (< 60s)
2. **Use caching**: For slow checks use interval subdirectory
3. **Catch errors**: Always output status 3 (UNKNOWN) on errors
4. **Unique names**: Service names should be unique
5. **Use metrics**: For graphs output metrics with thresholds
