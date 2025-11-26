# Spool Directory

The spool directory allows external programs to write agent output directly to files, which the CheckMK agent collects and integrates into its output. This is useful for long-running processes, cronjobs, backup monitoring, and testing check plugins.

## Use Cases

- Monitoring backup jobs (write result when backup completes)
- Long-running log analysis (avoid re-reading entire logs)
- Database statistics collection
- Cronjob result reporting
- Testing check plugin output during development
- Any process that runs independently of agent execution

## Directory Paths

| OS | Default Path |
|----|--------------|
| Linux/Unix | `/var/lib/check_mk_agent/spool/` |
| Windows | `C:\ProgramData\checkmk\agent\spool\` |

To find the configured path on a monitored host:

```bash
check_mk_agent | grep SpoolDirectory
# Output: SpoolDirectory: /var/lib/check_mk_agent/spool
```

## File Format

Spool files must contain valid agent output format:

```
<<<section_name>>>
data line 1
data line 2

<<<local>>>
0 "Service Name" metric=value Status text
```

### Requirements

1. **Start with section header**: `<<<section_name>>>`
2. **End with newline**: File must end with a newline character
3. **UTF-8 encoding**: No BOM, no UTF-16
4. **Unix line endings**: `\n` only, not `\r\n`

## File Naming

### Basic Names

Any filename without a leading dot works:

```
mycheck.txt
backup_status
_sorted_first.txt   # Underscore prefix for sorting
```

Files starting with `.` are ignored (use for documentation).

### Age Check (Staleness Detection)

Prefix filename with seconds for automatic staleness detection:

```
600_mycheck.txt     # Stale after 10 minutes
3600_hourly_job.txt # Stale after 1 hour
86400_daily_backup  # Stale after 24 hours
```

If the file is older than the prefix value, the agent ignores it and the service goes UNKNOWN.

**Example**: For a cronjob running every hour with ~5 min runtime:
```
3900_hourly_cleaner.txt   # 65 minutes = 1 hour + 5 min buffer
```

## Examples

### Local Check Output

```bash
# /var/lib/check_mk_agent/spool/backup_status
<<<local>>>
0 "Backup Status" age=2|size=1024 Last backup: 2 hours ago, 1024 MB
```

### Custom Section (Requires Check Plugin)

```bash
# /var/lib/check_mk_agent/spool/waterlevels
<<<waterlevels>>>
rainbarrel 376
pond 15212
pool 123732
```

### Multiple Sections

```bash
# /var/lib/check_mk_agent/spool/600_app_status
<<<app_health>>>
status running
uptime 86400
connections 150

<<<local>>>
0 "App Health" connections=150 Application running, 150 connections
```

### Piggyback Data

When using piggyback, always terminate with `<<<<>>>>`:

```bash
# /var/lib/check_mk_agent/spool/vm_status
<<<local>>>
0 "Hypervisor Status" - All VMs running

<<<<vm-web-01>>>>
<<<local>>>
0 "VM Status" - Running

<<<<vm-db-01>>>>
<<<local>>>
0 "VM Status" - Running

<<<<>>>>
```

**Important**: The `<<<<>>>>` line ensures subsequent output goes back to the main host.

## Practical Example: Backup Monitor

### Bash Script

```bash
#!/bin/bash
# /usr/local/bin/backup_monitor.sh
# Run this from your backup script or cron

SPOOL_DIR="/var/lib/check_mk_agent/spool"
SPOOL_FILE="${SPOOL_DIR}/3600_backup_status"

# Perform backup
BACKUP_START=$(date +%s)
/usr/local/bin/do_backup.sh
BACKUP_RESULT=$?
BACKUP_END=$(date +%s)
BACKUP_DURATION=$((BACKUP_END - BACKUP_START))

# Get backup size
BACKUP_SIZE=$(du -sm /var/backups/latest.tar.gz 2>/dev/null | cut -f1)

# Write spool file atomically
TEMP_FILE=$(mktemp)

if [[ $BACKUP_RESULT -eq 0 ]]; then
    cat > "$TEMP_FILE" << EOF
<<<local>>>
0 "Backup Status" duration=${BACKUP_DURATION}|size=${BACKUP_SIZE:-0} Backup completed in ${BACKUP_DURATION}s, Size: ${BACKUP_SIZE:-unknown} MB
EOF
else
    cat > "$TEMP_FILE" << EOF
<<<local>>>
2 "Backup Status" duration=${BACKUP_DURATION} Backup FAILED after ${BACKUP_DURATION}s (exit code: ${BACKUP_RESULT})
EOF
fi

# Atomic move to spool directory
mv "$TEMP_FILE" "$SPOOL_FILE"
chmod 644 "$SPOOL_FILE"
```

### PowerShell Script (Windows)

```powershell
# C:\Scripts\backup_monitor.ps1

$SpoolDir = "C:\ProgramData\checkmk\agent\spool"
$SpoolFile = Join-Path $SpoolDir "3600_backup_status"
$TempFile = [System.IO.Path]::GetTempFileName()

# Ensure UTF-8 without BOM
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false

try {
    # Perform backup
    $StartTime = Get-Date
    $BackupResult = & C:\Scripts\do_backup.ps1
    $EndTime = Get-Date
    $Duration = [int]($EndTime - $StartTime).TotalSeconds
    
    # Get backup info
    $BackupFile = Get-Item "C:\Backups\latest.zip" -ErrorAction SilentlyContinue
    $SizeMB = if ($BackupFile) { [int]($BackupFile.Length / 1MB) } else { 0 }
    
    if ($LASTEXITCODE -eq 0) {
        $Content = "<<<local>>>`n0 `"Backup Status`" duration=$Duration|size=$SizeMB Backup OK: ${Duration}s, ${SizeMB} MB`n"
    } else {
        $Content = "<<<local>>>`n2 `"Backup Status`" duration=$Duration Backup FAILED (exit: $LASTEXITCODE)`n"
    }
}
catch {
    $Content = "<<<local>>>`n2 `"Backup Status`" - Backup script error: $($_.Exception.Message)`n"
}

# Write with correct encoding
[System.IO.File]::WriteAllText($TempFile, $Content, $Utf8NoBom)

# Atomic move
Move-Item -Path $TempFile -Destination $SpoolFile -Force
```

### Python Script (Cross-platform)

```python
#!/usr/bin/env python3
"""
Backup monitor that writes to spool directory.
"""

import os
import sys
import tempfile
import shutil
import subprocess
import time
from pathlib import Path

# Platform-specific spool directory
if sys.platform == "win32":
    SPOOL_DIR = Path(r"C:\ProgramData\checkmk\agent\spool")
else:
    SPOOL_DIR = Path("/var/lib/check_mk_agent/spool")

SPOOL_FILE = SPOOL_DIR / "3600_backup_status"


def write_spool_file(content: str) -> None:
    """Write content to spool file atomically."""
    # Create temp file
    fd, temp_path = tempfile.mkstemp(suffix=".tmp")
    try:
        # Write with UTF-8, Unix line endings
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
            if not content.endswith('\n'):
                f.write('\n')
        
        # Atomic move
        shutil.move(temp_path, SPOOL_FILE)
        
        # Set permissions (Linux/Unix)
        if sys.platform != "win32":
            os.chmod(SPOOL_FILE, 0o644)
    except Exception:
        # Clean up temp file on error
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def run_backup() -> tuple[int, int, int]:
    """Run backup and return (exit_code, duration_seconds, size_mb)."""
    start_time = time.time()
    
    try:
        result = subprocess.run(
            ["/usr/local/bin/do_backup.sh"],
            capture_output=True,
            timeout=7200  # 2 hour timeout
        )
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        exit_code = -1
    except Exception:
        exit_code = -2
    
    duration = int(time.time() - start_time)
    
    # Get backup size
    backup_path = Path("/var/backups/latest.tar.gz")
    size_mb = int(backup_path.stat().st_size / (1024 * 1024)) if backup_path.exists() else 0
    
    return exit_code, duration, size_mb


def main():
    exit_code, duration, size_mb = run_backup()
    
    if exit_code == 0:
        content = (
            f'<<<local>>>\n'
            f'0 "Backup Status" duration={duration}|size={size_mb} '
            f'Backup completed in {duration}s, Size: {size_mb} MB\n'
        )
    else:
        content = (
            f'<<<local>>>\n'
            f'2 "Backup Status" duration={duration} '
            f'Backup FAILED (exit code: {exit_code})\n'
        )
    
    write_spool_file(content)


if __name__ == "__main__":
    main()
```

## Long-Running Daemon Example

For continuously running processes that update status periodically:

```python
#!/usr/bin/env python3
"""
Daemon that monitors a service and updates spool file.
"""

import time
import signal
import sys
from pathlib import Path

SPOOL_DIR = Path("/var/lib/check_mk_agent/spool")
SPOOL_FILE = SPOOL_DIR / "300_service_monitor"  # Stale after 5 minutes
UPDATE_INTERVAL = 60  # Update every minute

running = True

def signal_handler(signum, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def check_service() -> tuple[int, str, dict]:
    """Check service and return (status, message, metrics)."""
    # Your monitoring logic here
    # Return: status (0=OK, 1=WARN, 2=CRIT), message, metrics dict
    return 0, "Service is healthy", {"connections": 42, "latency": 5}


def write_status(status: int, message: str, metrics: dict) -> None:
    """Write current status to spool file."""
    metrics_str = "|".join(f"{k}={v}" for k, v in metrics.items())
    
    content = f'<<<local>>>\n{status} "Service Monitor" {metrics_str} {message}\n'
    
    # Write atomically
    temp_file = SPOOL_FILE.with_suffix('.tmp')
    temp_file.write_text(content, encoding='utf-8')
    temp_file.rename(SPOOL_FILE)


def main():
    while running:
        try:
            status, message, metrics = check_service()
            write_status(status, message, metrics)
        except Exception as e:
            write_status(3, f"Monitor error: {e}", {})
        
        # Sleep in small increments for responsive shutdown
        for _ in range(UPDATE_INTERVAL):
            if not running:
                break
            time.sleep(1)
    
    # Clean up on exit
    if SPOOL_FILE.exists():
        SPOOL_FILE.unlink()


if __name__ == "__main__":
    main()
```

## Important Considerations

### Character Encoding

| Requirement | Details |
|-------------|---------|
| Encoding | UTF-8 only (no UTF-16, no Windows-1252) |
| BOM | No Byte Order Mark |
| Line endings | Unix `\n` only, not Windows `\r\n` |
| ASCII fallback | If UTF-8 problematic, use 7-bit ASCII only |

**Windows PowerShell tip**:
```powershell
# Force UTF-8 without BOM
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($path, $content, $Utf8NoBom)
```

### Atomic Writes

Always write atomically to avoid partial reads:

```bash
# Bash: Write to temp, then move
TEMP=$(mktemp)
echo "<<<local>>>" > "$TEMP"
echo "0 \"My Check\" - OK" >> "$TEMP"
mv "$TEMP" /var/lib/check_mk_agent/spool/mycheck
```

```python
# Python: Write to temp, then rename
import tempfile
import shutil

fd, temp = tempfile.mkstemp()
with os.fdopen(fd, 'w') as f:
    f.write(content)
shutil.move(temp, spool_file)
```

### File Permissions

The spool directory is owned by root. For unprivileged users:

```bash
# Create empty file owned by specific user
touch /var/lib/check_mk_agent/spool/user_check
chown myuser:myuser /var/lib/check_mk_agent/spool/user_check
# User can now write to this file
```

### Soft Links and Named Pipes

- Soft links work but age check uses link's mtime, not target's
- Named pipes work but writer must always supply data (agent waits indefinitely)

### Documentation Files

Create hidden documentation files for each spool file:

```bash
# Spool file
/var/lib/check_mk_agent/spool/3600_backup

# Documentation (ignored by agent)
/var/lib/check_mk_agent/spool/.3600_backup
# Contents: Created by backup.sh, contact: admin@example.com
```

## Debugging

### Check Spool File Content

```bash
# View spool files
ls -la /var/lib/check_mk_agent/spool/

# Check encoding (look for BOM or UTF-16)
hexdump -C /var/lib/check_mk_agent/spool/mycheck | head

# Check line endings
file /var/lib/check_mk_agent/spool/mycheck

# View in agent output
check_mk_agent | grep -A5 "<<<local>>>"
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Service missing | Section header missing | Add `<<<local>>>` or appropriate header |
| Garbled output | Wrong encoding | Use UTF-8, no BOM |
| Partial data | Non-atomic write | Write to temp file, then move |
| UNKNOWN status | Stale file (age prefix) | File older than prefix seconds |
| Agent hangs | Named pipe with no writer | Ensure writer process runs |

## Best Practices

1. **Always use atomic writes** - Write to temp file, then move
2. **Use age prefixes** - Detect stale/crashed jobs automatically
3. **End with newline** - Ensure file ends with `\n`
4. **Use section headers** - Start with `<<<section_name>>>`
5. **Terminate piggyback** - End piggyback sections with `<<<<>>>>`
6. **Document spool files** - Use hidden `.filename` for documentation
7. **Handle errors** - Write error status if job fails
8. **UTF-8 only** - No BOM, Unix line endings
