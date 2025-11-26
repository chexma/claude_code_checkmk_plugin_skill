#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CheckMK Agent Plugin Template for Linux

This plugin template demonstrates best practices based on official CheckMK
plugins like mk_docker.py and mk_mongodb.py.

INSTALLATION:
    Copy to /usr/lib/check_mk_agent/plugins/mk_myapp

    For async execution (e.g., every 5 minutes):
    Copy to /usr/lib/check_mk_agent/plugins/300/mk_myapp

CONFIGURATION:
    Create /etc/check_mk/myapp.cfg (optional)
    See agents/cfg_examples/ for configuration templates

REQUIREMENTS:
    - Python 3.6+
    - Optional: specific Python packages (document here)

MANUAL TEST:
    /usr/lib/check_mk_agent/plugins/mk_myapp

Copyright (C) 2024 Your Name
License: GNU General Public License v2
"""

from __future__ import annotations

import configparser
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence

# ============================================================================
# CONSTANTS
# ============================================================================

# Version of this plugin
__version__ = "1.0.0"

# Section names output by this plugin
SECTION_NAME = "myapp"
SECTION_STATUS = "myapp_status"
SECTION_METRICS = "myapp_metrics"

# Default configuration
DEFAULT_CONFIG = {
    "enabled": True,
    "timeout": 30,
    "debug": False,
    "skip_sections": [],  # Sections to skip, e.g., ["metrics", "status"]
}

# ============================================================================
# ENVIRONMENT & PATHS
# ============================================================================

def get_config_dir() -> Path:
    """Get the configuration directory.
    
    The agent sets MK_CONFDIR environment variable.
    Fallback to /etc/check_mk for manual execution.
    """
    return Path(os.environ.get("MK_CONFDIR", "/etc/check_mk"))


def get_temp_dir() -> Path:
    """Get temporary directory for caching."""
    return Path(os.environ.get("MK_TEMPDIR", "/tmp"))


def get_state_dir() -> Path:
    """Get state directory for persistent data."""
    # MK_VARDIR is typically /var/lib/check_mk_agent
    return Path(os.environ.get("MK_VARDIR", "/var/lib/check_mk_agent"))


# ============================================================================
# CONFIGURATION
# ============================================================================

def read_config() -> Dict[str, Any]:
    """Read configuration from INI-style config file.
    
    Config file format (myapp.cfg):
    
        [MYAPP]
        enabled = true
        timeout = 60
        debug = false
        skip_sections = metrics,status
    
    Returns:
        Dictionary with configuration values
    """
    config = DEFAULT_CONFIG.copy()
    config_file = get_config_dir() / "myapp.cfg"
    
    if not config_file.exists():
        return config
    
    parser = configparser.ConfigParser()
    try:
        parser.read(str(config_file))
    except configparser.Error as e:
        sys.stderr.write(f"Error reading config: {e}\n")
        return config
    
    if not parser.has_section("MYAPP"):
        return config
    
    # Boolean values
    for key in ("enabled", "debug"):
        if parser.has_option("MYAPP", key):
            config[key] = parser.getboolean("MYAPP", key)
    
    # Integer values
    for key in ("timeout",):
        if parser.has_option("MYAPP", key):
            config[key] = parser.getint("MYAPP", key)
    
    # List values (comma-separated)
    if parser.has_option("MYAPP", "skip_sections"):
        value = parser.get("MYAPP", "skip_sections")
        config["skip_sections"] = [s.strip() for s in value.split(",") if s.strip()]
    
    return config


# ============================================================================
# OUTPUT HELPERS
# ============================================================================

def section_header(
    name: str,
    separator: Optional[int] = None,
    cached: Optional[tuple[int, int]] = None,
) -> str:
    """Generate a section header.
    
    Args:
        name: Section name
        separator: Optional separator character code (e.g., 0 for null, 124 for pipe)
        cached: Optional tuple of (timestamp, max_cache_age) for cached sections
    
    Returns:
        Formatted section header string
    """
    header = f"<<<{name}"
    
    if separator is not None:
        header += f":sep({separator})"
    
    if cached is not None:
        timestamp, max_age = cached
        header += f":cached({timestamp},{max_age})"
    
    header += ">>>"
    return header


def output_section(
    name: str,
    data: Sequence[str],
    separator: Optional[int] = None,
) -> None:
    """Output a complete section with header and data lines.
    
    Args:
        name: Section name
        data: List of data lines to output
        separator: Optional separator character code
    """
    print(section_header(name, separator))
    for line in data:
        print(line)


def output_json_section(name: str, data: Any) -> None:
    """Output a section with JSON data (separator 0)."""
    print(section_header(name, separator=0))
    print(json.dumps(data))


# ============================================================================
# DATA COLLECTION FUNCTIONS
# ============================================================================

def collect_service_status() -> Iterator[str]:
    """Collect systemd service status.
    
    Yields:
        Lines in format: service_name|status|substate|description
    """
    services = ["myapp", "myapp-worker"]  # Services to check
    
    for service in services:
        try:
            result = subprocess.run(
                ["systemctl", "show", service, "--property=ActiveState,SubState,Description"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode != 0:
                yield f"{service}|not-found|not-found|Service not installed"
                continue
            
            props = {}
            for line in result.stdout.strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    props[key] = value
            
            yield "|".join([
                service,
                props.get("ActiveState", "unknown"),
                props.get("SubState", "unknown"),
                props.get("Description", "").replace("|", " "),
            ])
            
        except subprocess.TimeoutExpired:
            yield f"{service}|timeout|timeout|Query timed out"
        except Exception as e:
            yield f"{service}|error|error|{str(e).replace('|', ' ')}"


def collect_process_info() -> Iterator[str]:
    """Collect process information.
    
    Yields:
        Lines in format: pid|name|cpu|memory_mb|threads|cmdline
    """
    process_names = ["myapp", "myapp-worker"]
    
    for name in process_names:
        try:
            # Find PIDs
            result = subprocess.run(
                ["pgrep", "-f", name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            if result.returncode != 0:
                continue
            
            for pid in result.stdout.strip().split("\n"):
                if not pid:
                    continue
                
                proc_dir = Path(f"/proc/{pid}")
                if not proc_dir.exists():
                    continue
                
                # Read process stats
                try:
                    stat = (proc_dir / "stat").read_text().split()
                    cmdline = (proc_dir / "cmdline").read_text().replace("\x00", " ").strip()
                    
                    # Memory from statm (pages)
                    statm = (proc_dir / "statm").read_text().split()
                    mem_pages = int(statm[1])  # RSS
                    mem_mb = (mem_pages * 4096) / (1024 * 1024)  # Assume 4K pages
                    
                    yield "|".join([
                        pid,
                        stat[1].strip("()"),  # Process name
                        stat[13],  # utime (CPU)
                        f"{mem_mb:.1f}",
                        stat[19],  # num_threads
                        cmdline[:200],
                    ])
                except (IOError, IndexError):
                    continue
                    
        except subprocess.TimeoutExpired:
            continue
        except Exception:
            continue


def collect_application_metrics() -> Dict[str, Any]:
    """Collect application-specific metrics.
    
    Returns:
        Dictionary with metric values
    """
    metrics = {
        "timestamp": int(time.time()),
        "version": "unknown",
        "status": "unknown",
    }
    
    # Example: Read from application status file
    status_file = Path("/var/lib/myapp/status.json")
    if status_file.exists():
        try:
            with open(status_file) as f:
                app_status = json.load(f)
            metrics.update({
                "version": app_status.get("version", "unknown"),
                "status": app_status.get("status", "unknown"),
                "queue_size": app_status.get("queue_size", 0),
                "processed_total": app_status.get("processed_total", 0),
                "errors_total": app_status.get("errors_total", 0),
            })
        except (json.JSONDecodeError, IOError):
            pass
    
    # Example: Query local HTTP endpoint
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:8080/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            health = json.loads(resp.read().decode())
            metrics["api_status"] = health.get("status", "unknown")
            metrics["uptime_seconds"] = health.get("uptime", 0)
    except Exception:
        metrics["api_status"] = "unreachable"
    
    return metrics


def collect_log_errors() -> Iterator[str]:
    """Collect recent errors from application log.
    
    Yields:
        Lines in format: timestamp|level|message
    """
    log_file = Path("/var/log/myapp/error.log")
    
    if not log_file.exists():
        return
    
    # Get last 20 lines
    try:
        result = subprocess.run(
            ["tail", "-n", "20", str(log_file)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            # Assume format: 2024-01-15 10:30:00 ERROR message
            parts = line.split(" ", 3)
            if len(parts) >= 4:
                timestamp = f"{parts[0]} {parts[1]}"
                level = parts[2]
                message = parts[3].replace("|", " ")[:200]
                yield f"{timestamp}|{level}|{message}"
                
    except Exception:
        pass


def collect_resource_usage() -> Iterator[str]:
    """Collect resource usage metrics.
    
    Yields:
        Lines in format: metric_name;value
    """
    # Disk usage for application directories
    for path in ["/var/lib/myapp", "/var/log/myapp"]:
        if Path(path).exists():
            try:
                result = subprocess.run(
                    ["du", "-sb", path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    size_bytes = result.stdout.split()[0]
                    name = path.replace("/", "_").strip("_")
                    yield f"disk_{name};{size_bytes}"
            except Exception:
                pass
    
    # File descriptor count
    try:
        result = subprocess.run(
            ["sh", "-c", "ls /proc/*/fd 2>/dev/null | wc -l"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            yield f"total_fds;{result.stdout.strip()}"
    except Exception:
        pass


# ============================================================================
# PIGGYBACK SUPPORT
# ============================================================================

def output_piggyback_start(hostname: str) -> None:
    """Start a piggyback section for another host."""
    print(f"<<<<{hostname}>>>>")


def output_piggyback_end() -> None:
    """End the current piggyback section."""
    print("<<<<>>>>")


def collect_container_data() -> None:
    """Example: Collect data for containers and output as piggyback.
    
    This demonstrates how to output data for other hosts (like Docker containers).
    """
    # This is just an example - adapt for your use case
    containers_file = Path("/var/lib/myapp/containers.json")
    
    if not containers_file.exists():
        return
    
    try:
        with open(containers_file) as f:
            containers = json.load(f)
    except Exception:
        return
    
    for container in containers:
        container_name = container.get("name", "").lower()
        if not container_name:
            continue
        
        # Start piggyback for this container
        output_piggyback_start(container_name)
        
        # Output container-specific sections
        print(section_header("myapp_container", separator=59))
        print(f"id;{container.get('id', '')}")
        print(f"status;{container.get('status', 'unknown')}")
        print(f"cpu;{container.get('cpu_percent', 0)}")
        print(f"memory;{container.get('memory_mb', 0)}")
        
        # End piggyback
        output_piggyback_end()


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    """Main entry point.
    
    Returns:
        Exit code (0 for success)
    """
    # Read configuration
    config = read_config()
    
    # Check if plugin is enabled
    if not config.get("enabled", True):
        return 0
    
    skip_sections = config.get("skip_sections", [])
    
    # Debug output (to stderr, not stdout)
    if config.get("debug"):
        sys.stderr.write(f"myapp plugin v{__version__} starting\n")
        sys.stderr.write(f"Config: {config}\n")
    
    try:
        # Section: Service Status (pipe-separated)
        if "status" not in skip_sections:
            output_section(
                SECTION_STATUS,
                list(collect_service_status()),
                separator=124,  # Pipe
            )
        
        # Section: Process Info (pipe-separated)
        if "processes" not in skip_sections:
            output_section(
                f"{SECTION_NAME}_processes",
                list(collect_process_info()),
                separator=124,
            )
        
        # Section: Application Metrics (JSON)
        if "metrics" not in skip_sections:
            metrics = collect_application_metrics()
            output_json_section(SECTION_METRICS, metrics)
        
        # Section: Resource Usage (semicolon-separated)
        if "resources" not in skip_sections:
            output_section(
                f"{SECTION_NAME}_resources",
                list(collect_resource_usage()),
                separator=59,  # Semicolon
            )
        
        # Section: Log Errors (pipe-separated)
        if "logs" not in skip_sections:
            output_section(
                f"{SECTION_NAME}_logs",
                list(collect_log_errors()),
                separator=124,
            )
        
        # Piggyback data for sub-resources (if applicable)
        if "piggyback" not in skip_sections:
            collect_container_data()
        
    except Exception as e:
        if config.get("debug"):
            sys.stderr.write(f"Error: {e}\n")
            import traceback
            traceback.print_exc(file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
