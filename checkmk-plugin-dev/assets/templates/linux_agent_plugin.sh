#!/bin/bash
# CheckMK Agent Plugin Template for Linux (Bash)
#
# INSTALLATION:
#     Copy to /usr/lib/check_mk_agent/plugins/mk_myapp
#     chmod 755 /usr/lib/check_mk_agent/plugins/mk_myapp
#
#     For async execution (e.g., every 5 minutes):
#     mkdir -p /usr/lib/check_mk_agent/plugins/300
#     Copy to /usr/lib/check_mk_agent/plugins/300/mk_myapp
#
# CONFIGURATION:
#     Create /etc/check_mk/myapp.cfg (optional)
#
# MANUAL TEST:
#     /usr/lib/check_mk_agent/plugins/mk_myapp
#
# Copyright (C) 2024 Your Name
# License: GNU General Public License v2

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================

# Config directory (set by agent, fallback for manual testing)
MK_CONFDIR="${MK_CONFDIR:-/etc/check_mk}"
MK_VARDIR="${MK_VARDIR:-/var/lib/check_mk_agent}"
MK_TEMPDIR="${MK_TEMPDIR:-/tmp}"

# Default configuration
ENABLED=true
DEBUG=false
SERVICE_NAME="myapp"
LOG_FILE="/var/log/myapp/app.log"
TIMEOUT=30

# Read configuration file if it exists
CONFIG_FILE="${MK_CONFDIR}/myapp.cfg"
if [[ -f "$CONFIG_FILE" ]]; then
    # Source simple key=value config
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
        # Remove leading/trailing whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        case "$key" in
            enabled)  ENABLED="$value" ;;
            debug)    DEBUG="$value" ;;
            service)  SERVICE_NAME="$value" ;;
            log_file) LOG_FILE="$value" ;;
            timeout)  TIMEOUT="$value" ;;
        esac
    done < "$CONFIG_FILE"
fi

# Exit if disabled
if [[ "$ENABLED" != "true" && "$ENABLED" != "1" && "$ENABLED" != "yes" ]]; then
    exit 0
fi

# Debug helper
debug() {
    if [[ "$DEBUG" == "true" || "$DEBUG" == "1" ]]; then
        echo "# DEBUG: $*" >&2
    fi
}

debug "Starting myapp plugin"
debug "Config: SERVICE_NAME=$SERVICE_NAME, LOG_FILE=$LOG_FILE"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Output section header
# Usage: section_header "section_name" [separator]
section_header() {
    local name="$1"
    local sep="$2"
    
    if [[ -n "$sep" ]]; then
        echo "<<<${name}:sep(${sep})>>>"
    else
        echo "<<<${name}>>>"
    fi
}

# Safe command execution with timeout
# Usage: safe_exec command arg1 arg2 ...
safe_exec() {
    timeout "$TIMEOUT" "$@" 2>/dev/null || true
}

# ============================================================================
# DATA COLLECTION
# ============================================================================

# Section: Service Status
collect_service_status() {
    section_header "myapp_service" 124  # Pipe separator
    
    if command -v systemctl &>/dev/null; then
        # Systemd
        local status
        status=$(systemctl is-active "$SERVICE_NAME" 2>/dev/null || echo "not-found")
        local substate
        substate=$(systemctl show "$SERVICE_NAME" --property=SubState --value 2>/dev/null || echo "unknown")
        
        echo "${SERVICE_NAME}|${status}|${substate}"
    else
        # SysVinit fallback
        if service "$SERVICE_NAME" status &>/dev/null; then
            echo "${SERVICE_NAME}|active|running"
        else
            echo "${SERVICE_NAME}|inactive|dead"
        fi
    fi
}

# Section: Process Information
collect_process_info() {
    section_header "myapp_processes" 124  # Pipe separator
    
    # Find processes and output info
    # Format: pid|name|cpu%|mem%|threads|cmdline
    if command -v pgrep &>/dev/null; then
        local pids
        pids=$(pgrep -f "$SERVICE_NAME" 2>/dev/null || true)
        
        for pid in $pids; do
            if [[ -d "/proc/$pid" ]]; then
                local name cpu mem threads cmdline
                name=$(cat "/proc/$pid/comm" 2>/dev/null || echo "unknown")
                
                # Get CPU and memory from ps
                read -r cpu mem <<< "$(ps -p "$pid" -o %cpu=,%mem= 2>/dev/null || echo "0 0")"
                
                # Thread count from /proc
                threads=$(ls -1 "/proc/$pid/task" 2>/dev/null | wc -l || echo "1")
                
                # Command line (truncated)
                cmdline=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | head -c 200 || echo "")
                
                echo "${pid}|${name}|${cpu}|${mem}|${threads}|${cmdline}"
            fi
        done
    fi
}

# Section: Application Metrics
collect_metrics() {
    section_header "myapp_metrics" 59  # Semicolon separator
    
    # Example: Read from application status file
    local status_file="/var/lib/${SERVICE_NAME}/status"
    if [[ -f "$status_file" ]]; then
        while IFS='=' read -r key value; do
            [[ -z "$key" || "$key" =~ ^# ]] && continue
            echo "${key};${value}"
        done < "$status_file"
    fi
    
    # Example: Query application via socket or HTTP
    if command -v curl &>/dev/null; then
        local health
        health=$(safe_exec curl -s -m 5 "http://localhost:8080/health" 2>/dev/null || echo "{}")
        
        # Parse JSON with jq if available, otherwise simple grep
        if command -v jq &>/dev/null; then
            local status uptime
            status=$(echo "$health" | jq -r '.status // "unknown"')
            uptime=$(echo "$health" | jq -r '.uptime // 0')
            echo "api_status;${status}"
            echo "uptime_seconds;${uptime}"
        fi
    fi
}

# Section: Disk Usage
collect_disk_usage() {
    section_header "myapp_disk" 59  # Semicolon separator
    
    for path in "/var/lib/${SERVICE_NAME}" "/var/log/${SERVICE_NAME}"; do
        if [[ -d "$path" ]]; then
            local size
            size=$(du -sb "$path" 2>/dev/null | cut -f1 || echo "0")
            local name
            name=$(echo "$path" | tr '/' '_' | sed 's/^_//')
            echo "${name};${size}"
        fi
    done
}

# Section: Log Errors (last N errors)
collect_log_errors() {
    section_header "myapp_logs" 124  # Pipe separator
    
    if [[ -f "$LOG_FILE" ]]; then
        # Get last 10 error lines
        grep -i "error\|critical\|fatal" "$LOG_FILE" 2>/dev/null | tail -10 | while read -r line; do
            # Escape pipe characters
            line="${line//|/ }"
            # Truncate long lines
            echo "${line:0:500}"
        done
    fi
}

# Section: Custom Checks
collect_custom_checks() {
    section_header "myapp_custom" 0  # No separator (space)
    
    # Example: Check if required files exist
    local config_ok=0
    local data_ok=0
    
    [[ -f "/etc/${SERVICE_NAME}/${SERVICE_NAME}.conf" ]] && config_ok=1
    [[ -d "/var/lib/${SERVICE_NAME}/data" ]] && data_ok=1
    
    echo "config_exists $config_ok"
    echo "data_dir_exists $data_ok"
    
    # Example: Check listening port
    if command -v ss &>/dev/null; then
        if ss -tlnp 2>/dev/null | grep -q ":8080"; then
            echo "port_8080 listening"
        else
            echo "port_8080 closed"
        fi
    fi
}

# ============================================================================
# PIGGYBACK SUPPORT
# ============================================================================

# Start piggyback section for another host
piggyback_start() {
    echo "<<<<$1>>>>"
}

# End piggyback section
piggyback_end() {
    echo "<<<<>>>>"
}

# Example: Collect data for sub-resources
collect_piggyback_data() {
    # Example: Output data for worker processes as separate hosts
    local workers_file="/var/lib/${SERVICE_NAME}/workers.list"
    
    if [[ -f "$workers_file" ]]; then
        while read -r worker_name worker_status; do
            [[ -z "$worker_name" ]] && continue
            
            piggyback_start "$worker_name"
            
            section_header "myapp_worker" 59
            echo "name;${worker_name}"
            echo "status;${worker_status}"
            
            piggyback_end
        done < "$workers_file"
    fi
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    # Collect all sections
    collect_service_status
    collect_process_info
    collect_metrics
    collect_disk_usage
    collect_log_errors
    collect_custom_checks
    
    # Piggyback data (optional)
    # collect_piggyback_data
    
    debug "Plugin finished"
}

# Run main function
main

exit 0
