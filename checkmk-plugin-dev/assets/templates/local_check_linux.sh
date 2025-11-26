#!/bin/bash
# =============================================================================
# CheckMK Local Check Template - Bash
# =============================================================================
#
# Installation:
#   Linux:   /usr/lib/check_mk_agent/local/
#   FreeBSD: /usr/local/lib/check_mk_agent/local/
#
# For cached/async execution, place in interval subdirectory:
#   /usr/lib/check_mk_agent/local/300/   (every 5 minutes)
#   /usr/lib/check_mk_agent/local/600/   (every 10 minutes)
#   /usr/lib/check_mk_agent/local/3600/  (every hour)
#
# Make executable: chmod +x <scriptname>
#
# Output format per line:
#   <STATUS> "<SERVICE_NAME>" <METRICS> <STATUS_TEXT>
#
# Status values:
#   0 = OK, 1 = WARN, 2 = CRIT, 3 = UNKNOWN, P = dynamic (from thresholds)
#
# =============================================================================

# Configuration
readonly SERVICE_NAME="My Custom Check"
readonly WARN_THRESHOLD=80
readonly CRIT_THRESHOLD=90

# =============================================================================
# Helper Functions
# =============================================================================

# Output a local check result
# Usage: output_result <status> <service_name> <metrics> <text>
output_result() {
    local status="$1"
    local name="$2"
    local metrics="$3"
    local text="$4"
    echo "${status} \"${name}\" ${metrics} ${text}"
}

# Output OK result
output_ok() {
    output_result 0 "$1" "$2" "$3"
}

# Output WARN result
output_warn() {
    output_result 1 "$1" "$2" "$3"
}

# Output CRIT result
output_crit() {
    output_result 2 "$1" "$2" "$3"
}

# Output UNKNOWN result
output_unknown() {
    output_result 3 "$1" "$2" "$3"
}

# Output with dynamic state calculation
output_dynamic() {
    output_result P "$1" "$2" "$3"
}

# Safe command execution with timeout
safe_exec() {
    local timeout_sec="${1:-10}"
    shift
    timeout "$timeout_sec" "$@" 2>/dev/null
}

# =============================================================================
# Example Checks - Customize or replace these
# =============================================================================

# Example 1: Simple static check
check_static_example() {
    output_ok "Static Example" "-" "This check is always OK"
}

# Example 2: Service status check
check_service() {
    local service_name="$1"
    
    if systemctl is-active --quiet "$service_name" 2>/dev/null; then
        output_ok "Service $service_name" "-" "Service is running"
    elif systemctl is-enabled --quiet "$service_name" 2>/dev/null; then
        output_crit "Service $service_name" "-" "Service is stopped but enabled"
    else
        output_warn "Service $service_name" "-" "Service is not enabled"
    fi
}

# Example 3: File age check
check_file_age() {
    local file_path="$1"
    local warn_hours="${2:-24}"
    local crit_hours="${3:-48}"
    local service_name="${4:-File Age}"
    
    if [[ ! -f "$file_path" ]]; then
        output_crit "$service_name" "-" "File not found: $file_path"
        return
    fi
    
    local file_time
    file_time=$(stat -c %Y "$file_path")
    local current_time
    current_time=$(date +%s)
    local age_hours=$(( (current_time - file_time) / 3600 ))
    
    # Use dynamic state calculation with thresholds
    output_dynamic "$service_name" "age=${age_hours};${warn_hours};${crit_hours}" \
        "File is ${age_hours} hours old"
}

# Example 4: Disk space check with metrics
check_disk_space() {
    local mount_point="${1:-/}"
    local warn_percent="${2:-80}"
    local crit_percent="${3:-90}"
    
    local usage
    usage=$(df -P "$mount_point" 2>/dev/null | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
    
    if [[ -z "$usage" ]]; then
        output_unknown "Disk $mount_point" "-" "Cannot read disk usage"
        return
    fi
    
    # Dynamic state calculation
    output_dynamic "Disk $mount_point" \
        "usage=${usage};${warn_percent};${crit_percent};0;100" \
        "Disk usage: ${usage}%"
}

# Example 5: Process count check
check_process_count() {
    local process_name="$1"
    local min_count="${2:-1}"
    local max_count="${3:-10}"
    
    local count
    count=$(pgrep -c "$process_name" 2>/dev/null || echo 0)
    
    if [[ $count -lt $min_count ]]; then
        output_crit "Process $process_name" "count=$count" \
            "Only $count processes (min: $min_count)"
    elif [[ $count -gt $max_count ]]; then
        output_warn "Process $process_name" "count=$count" \
            "Too many: $count processes (max: $max_count)"
    else
        output_ok "Process $process_name" "count=$count" \
            "$count processes running"
    fi
}

# Example 6: TCP port check
check_tcp_port() {
    local host="${1:-localhost}"
    local port="$2"
    local service_name="${3:-Port $port}"
    local timeout_sec="${4:-5}"
    
    if timeout "$timeout_sec" bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null; then
        output_ok "$service_name" "-" "Port $port is open on $host"
    else
        output_crit "$service_name" "-" "Port $port is closed on $host"
    fi
}

# Example 7: Log file error check
check_log_errors() {
    local log_file="$1"
    local pattern="${2:-ERROR|FATAL|CRITICAL}"
    local warn_count="${3:-1}"
    local crit_count="${4:-10}"
    local service_name="${5:-Log Errors}"
    
    if [[ ! -r "$log_file" ]]; then
        output_unknown "$service_name" "-" "Cannot read log file: $log_file"
        return
    fi
    
    # Count errors in last 1000 lines
    local error_count
    error_count=$(tail -1000 "$log_file" 2>/dev/null | grep -cE "$pattern" || echo 0)
    
    output_dynamic "$service_name" \
        "errors=${error_count};${warn_count};${crit_count}" \
        "Found $error_count errors in log"
}

# Example 8: Multiple metrics
check_system_load() {
    local warn_load="${1:-4}"
    local crit_load="${2:-8}"
    
    read -r load1 load5 load15 _ < /proc/loadavg
    
    # Multiple metrics separated by |
    local metrics="load1=${load1};${warn_load};${crit_load}"
    metrics="${metrics}|load5=${load5}"
    metrics="${metrics}|load15=${load15}"
    
    output_dynamic "System Load" "$metrics" "Load: $load1 / $load5 / $load15"
}

# Example 9: Backup check with complex logic
check_backup() {
    local backup_dir="${1:-/var/backups}"
    local pattern="${2:-*.tar.gz}"
    local max_age_hours="${3:-25}"
    local min_size_mb="${4:-10}"
    
    # Find newest backup
    local newest_backup
    newest_backup=$(find "$backup_dir" -name "$pattern" -type f -printf '%T@ %p\n' 2>/dev/null | \
                    sort -rn | head -1 | cut -d' ' -f2-)
    
    if [[ -z "$newest_backup" ]]; then
        output_crit "Backup Status" "-" "No backup files found in $backup_dir"
        return
    fi
    
    # Calculate age
    local backup_time
    backup_time=$(stat -c %Y "$newest_backup")
    local current_time
    current_time=$(date +%s)
    local age_hours=$(( (current_time - backup_time) / 3600 ))
    
    # Get size in MB
    local size_mb=$(( $(stat -c %s "$newest_backup") / 1024 / 1024 ))
    
    # Determine status
    local status=0
    local msg="Age: ${age_hours}h, Size: ${size_mb}MB"
    
    if [[ $age_hours -gt $max_age_hours ]]; then
        status=2
        msg="Backup too old: ${age_hours}h (max: ${max_age_hours}h)"
    elif [[ $size_mb -lt $min_size_mb ]]; then
        status=1
        msg="Backup small: ${size_mb}MB (min: ${min_size_mb}MB)"
    fi
    
    # Output with multiple metrics
    local metrics="age=${age_hours};${max_age_hours};$((max_age_hours * 2))"
    metrics="${metrics}|size=${size_mb};${min_size_mb}:"
    
    output_result "$status" "Backup Status" "$metrics" "$msg"
}

# =============================================================================
# Main - Run your checks here
# =============================================================================

main() {
    # Uncomment and customize the checks you need:
    
    check_static_example
    # check_service "nginx"
    # check_service "mysql"
    # check_file_age "/var/log/backup.log" 24 48 "Backup Log Age"
    # check_disk_space "/" 80 90
    # check_disk_space "/var" 85 95
    # check_process_count "nginx" 1 20
    # check_tcp_port "localhost" 80 "HTTP Port"
    # check_tcp_port "localhost" 443 "HTTPS Port"
    # check_log_errors "/var/log/app/error.log" "ERROR|FATAL" 5 20 "App Errors"
    # check_system_load 4 8
    # check_backup "/var/backups" "*.tar.gz" 25 10
}

main "$@"
