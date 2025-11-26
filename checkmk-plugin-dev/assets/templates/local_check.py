#!/usr/bin/env python3
# =============================================================================
# CheckMK Local Check Template - Python
# =============================================================================
#
# Installation:
#   Linux:   /usr/lib/check_mk_agent/local/
#   Windows: C:\ProgramData\checkmk\agent\local\
#
# For cached/async execution (Linux), place in interval subdirectory:
#   /usr/lib/check_mk_agent/local/300/   (every 5 minutes)
#   /usr/lib/check_mk_agent/local/600/   (every 10 minutes)
#
# Make executable (Linux): chmod +x <scriptname>
#
# Output format per line:
#   <STATUS> "<SERVICE_NAME>" <METRICS> <STATUS_TEXT>
#
# Status values:
#   0 = OK, 1 = WARN, 2 = CRIT, 3 = UNKNOWN, P = dynamic (from thresholds)
#
# =============================================================================

import os
import sys
import socket
import subprocess
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union, List, Tuple

# =============================================================================
# Constants
# =============================================================================

STATUS_OK = 0
STATUS_WARN = 1
STATUS_CRIT = 2
STATUS_UNKNOWN = 3
STATUS_DYNAMIC = "P"


# =============================================================================
# Helper Classes and Functions
# =============================================================================

class LocalCheck:
    """Helper class for outputting local check results."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.metrics: List[str] = []
    
    def add_metric(
        self,
        name: str,
        value: Union[int, float],
        warn: Optional[str] = None,
        crit: Optional[str] = None,
        min_val: Optional[Union[int, float]] = None,
        max_val: Optional[Union[int, float]] = None
    ) -> "LocalCheck":
        """Add a metric to the check output."""
        metric = f"{name}={value}"
        
        if warn is not None or crit is not None:
            metric += f";{warn or ''};{crit or ''}"
            if min_val is not None or max_val is not None:
                metric += f";{min_val if min_val is not None else ''}"
                metric += f";{max_val if max_val is not None else ''}"
        
        self.metrics.append(metric)
        return self
    
    def output(self, status: Union[int, str], text: str) -> None:
        """Output the check result in CheckMK format."""
        metrics_str = "|".join(self.metrics) if self.metrics else "-"
        print(f'{status} "{self.service_name}" {metrics_str} {text}')


def output_result(
    status: Union[int, str],
    service_name: str,
    metrics: str,
    text: str
) -> None:
    """Output a local check result in CheckMK format."""
    print(f'{status} "{service_name}" {metrics} {text}')


def output_ok(service_name: str, text: str, metrics: str = "-") -> None:
    """Output an OK result."""
    output_result(STATUS_OK, service_name, metrics, text)


def output_warn(service_name: str, text: str, metrics: str = "-") -> None:
    """Output a WARN result."""
    output_result(STATUS_WARN, service_name, metrics, text)


def output_crit(service_name: str, text: str, metrics: str = "-") -> None:
    """Output a CRIT result."""
    output_result(STATUS_CRIT, service_name, metrics, text)


def output_unknown(service_name: str, text: str, metrics: str = "-") -> None:
    """Output an UNKNOWN result."""
    output_result(STATUS_UNKNOWN, service_name, metrics, text)


def output_dynamic(service_name: str, metrics: str, text: str) -> None:
    """Output a result with dynamic state calculation."""
    output_result(STATUS_DYNAMIC, service_name, metrics, text)


# =============================================================================
# Example Checks - Customize or replace these
# =============================================================================

def check_static_example() -> None:
    """Example: Simple static check that is always OK."""
    output_ok("Static Example", "This check is always OK")


def check_disk_space(
    path: str = "/",
    warn_percent: int = 80,
    crit_percent: int = 90
) -> None:
    """Check disk space usage with dynamic thresholds."""
    try:
        total, used, free = shutil.disk_usage(path)
        used_percent = round((used / total) * 100, 1)
        total_gb = round(total / (1024**3), 1)
        used_gb = round(used / (1024**3), 1)
        
        metrics = f"usage={used_percent};{warn_percent};{crit_percent};0;100"
        output_dynamic(
            f"Disk {path}",
            metrics,
            f"Used: {used_percent}% ({used_gb} GB of {total_gb} GB)"
        )
    except Exception as e:
        output_unknown(f"Disk {path}", f"Cannot read disk: {e}")


def check_file_age(
    file_path: str,
    warn_hours: int = 24,
    crit_hours: int = 48,
    service_name: str = "File Age"
) -> None:
    """Check the age of a file."""
    path = Path(file_path)
    
    if not path.exists():
        output_crit(service_name, f"File not found: {file_path}")
        return
    
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        age = datetime.now() - mtime
        age_hours = round(age.total_seconds() / 3600, 1)
        
        metrics = f"age={age_hours};{warn_hours};{crit_hours}"
        output_dynamic(service_name, metrics, f"File is {age_hours} hours old")
    except Exception as e:
        output_unknown(service_name, f"Cannot check file: {e}")


def check_file_size(
    file_path: str,
    warn_mb: int = 100,
    crit_mb: int = 500,
    service_name: str = "File Size"
) -> None:
    """Check the size of a file."""
    path = Path(file_path)
    
    if not path.exists():
        output_crit(service_name, f"File not found: {file_path}")
        return
    
    try:
        size_bytes = path.stat().st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)
        
        metrics = f"size={size_mb};{warn_mb};{crit_mb}"
        output_dynamic(service_name, metrics, f"File size: {size_mb} MB")
    except Exception as e:
        output_unknown(service_name, f"Cannot check file: {e}")


def check_tcp_port(
    host: str = "localhost",
    port: int = 80,
    timeout: float = 5.0,
    service_name: Optional[str] = None
) -> None:
    """Check if a TCP port is reachable."""
    if service_name is None:
        service_name = f"Port {port}"
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            output_ok(service_name, f"Port {port} is open on {host}")
        else:
            output_crit(service_name, f"Port {port} is closed on {host}")
    except socket.timeout:
        output_crit(service_name, f"Connection timeout to {host}:{port}")
    except Exception as e:
        output_unknown(service_name, f"Cannot check port: {e}")


def check_process_count(
    process_name: str,
    min_count: int = 1,
    max_count: int = 100
) -> None:
    """Check if a process is running and count instances."""
    try:
        if sys.platform == "win32":
            # Windows
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {process_name}*", "/NH"],
                capture_output=True,
                text=True,
                timeout=10
            )
            # Count non-empty lines that contain the process name
            count = len([
                line for line in result.stdout.strip().split("\n")
                if process_name.lower() in line.lower()
            ])
        else:
            # Linux/Unix
            result = subprocess.run(
                ["pgrep", "-c", process_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            count = int(result.stdout.strip()) if result.returncode == 0 else 0
        
        metrics = f"count={count}"
        
        if count < min_count:
            output_crit(
                f"Process {process_name}",
                f"Only {count} instances (min: {min_count})",
                metrics
            )
        elif count > max_count:
            output_warn(
                f"Process {process_name}",
                f"Too many: {count} instances (max: {max_count})",
                metrics
            )
        else:
            output_ok(
                f"Process {process_name}",
                f"{count} instances running",
                metrics
            )
    except Exception as e:
        output_unknown(f"Process {process_name}", f"Cannot check process: {e}")


def check_command_output(
    command: List[str],
    expected_content: Optional[str] = None,
    service_name: str = "Command Check",
    timeout: int = 30
) -> None:
    """Run a command and check its output or exit code."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            output_crit(
                service_name,
                f"Command failed with exit code {result.returncode}"
            )
            return
        
        if expected_content:
            if expected_content in result.stdout:
                output_ok(service_name, "Expected content found")
            else:
                output_warn(service_name, "Expected content not found")
        else:
            output_ok(service_name, "Command executed successfully")
            
    except subprocess.TimeoutExpired:
        output_crit(service_name, f"Command timed out after {timeout}s")
    except Exception as e:
        output_unknown(service_name, f"Cannot run command: {e}")


def check_http_response(
    url: str,
    expected_status: int = 200,
    timeout: float = 10.0,
    service_name: Optional[str] = None
) -> None:
    """Check HTTP response status code."""
    if service_name is None:
        service_name = f"HTTP {url}"
    
    try:
        import urllib.request
        import urllib.error
        import time
        
        start_time = time.time()
        
        request = urllib.request.Request(url, method="GET")
        request.add_header("User-Agent", "CheckMK Local Check")
        
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status_code = response.status
                response_time = round((time.time() - start_time) * 1000, 0)
        except urllib.error.HTTPError as e:
            status_code = e.code
            response_time = round((time.time() - start_time) * 1000, 0)
        
        metrics = f"response_time={response_time};1000;5000|status={status_code}"
        
        if status_code == expected_status:
            output_ok(service_name, f"Status {status_code}, {response_time}ms", metrics)
        else:
            output_crit(
                service_name,
                f"Status {status_code} (expected {expected_status}), {response_time}ms",
                metrics
            )
            
    except Exception as e:
        output_crit(service_name, f"Request failed: {e}")


def check_directory_count(
    directory: str,
    pattern: str = "*",
    warn_count: int = 100,
    crit_count: int = 1000,
    service_name: str = "Directory Count"
) -> None:
    """Count files in a directory."""
    path = Path(directory)
    
    if not path.is_dir():
        output_crit(service_name, f"Directory not found: {directory}")
        return
    
    try:
        count = len(list(path.glob(pattern)))
        
        metrics = f"count={count};{warn_count};{crit_count}"
        output_dynamic(service_name, metrics, f"Found {count} files matching '{pattern}'")
    except Exception as e:
        output_unknown(service_name, f"Cannot count files: {e}")


def check_backup(
    backup_dir: str,
    pattern: str = "*.tar.gz",
    max_age_hours: int = 25,
    min_size_mb: int = 10,
    service_name: str = "Backup Status"
) -> None:
    """Check backup files for age and size."""
    path = Path(backup_dir)
    
    if not path.is_dir():
        output_crit(service_name, f"Backup directory not found: {backup_dir}")
        return
    
    try:
        # Find newest backup file
        backup_files = list(path.glob(pattern))
        
        if not backup_files:
            output_crit(service_name, f"No backup files found matching '{pattern}'")
            return
        
        newest = max(backup_files, key=lambda f: f.stat().st_mtime)
        
        # Calculate age
        mtime = datetime.fromtimestamp(newest.stat().st_mtime)
        age = datetime.now() - mtime
        age_hours = round(age.total_seconds() / 3600, 1)
        
        # Get size
        size_mb = round(newest.stat().st_size / (1024 * 1024), 1)
        
        # Build check object with metrics
        check = LocalCheck(service_name)
        check.add_metric("age", age_hours, str(max_age_hours), str(max_age_hours * 2))
        check.add_metric("size", size_mb, f"{min_size_mb}:")
        
        # Determine status
        if age_hours > max_age_hours:
            check.output(STATUS_CRIT, f"Backup too old: {age_hours}h (max: {max_age_hours}h)")
        elif size_mb < min_size_mb:
            check.output(STATUS_WARN, f"Backup small: {size_mb}MB (min: {min_size_mb}MB)")
        else:
            check.output(STATUS_OK, f"Age: {age_hours}h, Size: {size_mb}MB")
            
    except Exception as e:
        output_unknown(service_name, f"Cannot check backup: {e}")


def check_load_average(
    warn_load: float = 4.0,
    crit_load: float = 8.0
) -> None:
    """Check system load average (Linux/Unix only)."""
    if sys.platform == "win32":
        output_unknown("System Load", "Not available on Windows")
        return
    
    try:
        load1, load5, load15 = os.getloadavg()
        
        # Build metrics with multiple values
        metrics = f"load1={load1:.2f};{warn_load};{crit_load}"
        metrics += f"|load5={load5:.2f}"
        metrics += f"|load15={load15:.2f}"
        
        output_dynamic(
            "System Load",
            metrics,
            f"Load: {load1:.2f} / {load5:.2f} / {load15:.2f}"
        )
    except Exception as e:
        output_unknown("System Load", f"Cannot read load: {e}")


# =============================================================================
# Main - Run your checks here
# =============================================================================

def main():
    """Main function - uncomment and customize the checks you need."""
    
    check_static_example()
    
    # Disk space checks
    # check_disk_space("/", 80, 90)
    # check_disk_space("/var", 85, 95)
    
    # File checks
    # check_file_age("/var/log/backup.log", 24, 48, "Backup Log Age")
    # check_file_size("/var/log/app.log", 100, 500, "App Log Size")
    
    # Network checks
    # check_tcp_port("localhost", 80, 5.0, "HTTP Port")
    # check_tcp_port("localhost", 443, 5.0, "HTTPS Port")
    # check_tcp_port("localhost", 3306, 5.0, "MySQL Port")
    # check_http_response("http://localhost/health", 200, 10.0, "Health Endpoint")
    
    # Process checks
    # check_process_count("nginx", 1, 20)
    # check_process_count("python", 0, 50)
    
    # Command checks
    # check_command_output(["systemctl", "is-active", "nginx"], service_name="Nginx Status")
    
    # Directory checks
    # check_directory_count("/tmp", "*.tmp", 100, 1000, "Temp Files")
    
    # Backup checks
    # check_backup("/var/backups", "*.tar.gz", 25, 10)
    
    # System checks (Linux only)
    # check_load_average(4.0, 8.0)


if __name__ == "__main__":
    main()
