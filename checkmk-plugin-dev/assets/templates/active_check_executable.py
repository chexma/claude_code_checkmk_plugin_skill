#!/usr/bin/env python3
"""
Active Check Executable Template
================================
Location: ~/local/lib/nagios/plugins/check_myservice
          OR ~/local/lib/python3/cmk_addons/plugins/<family>/libexec/check_myservice

IMPORTANT: 
- No file extension! Name should be "check_myservice" not "check_myservice.py"
- Must be executable: chmod 755 check_myservice

Output Format (Nagios Plugin Standard):
STATUS_TEXT | metric1=value;warn;crit;min;max metric2=value;warn;crit

Exit Codes:
0 = OK
1 = WARNING  
2 = CRITICAL
3 = UNKNOWN

Usage:
    check_myservice -H hostname -p port [-w warning] [-c critical] [-t timeout]
"""

import argparse
import socket
import sys
import time
from typing import Optional, Tuple


# =============================================================================
# EXIT CODES
# =============================================================================
OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

def output_result(
    status: int,
    message: str,
    perfdata: Optional[dict] = None,
) -> None:
    """
    Print result in Nagios format and exit.
    
    Args:
        status: Exit code (0-3)
        message: Status message
        perfdata: Dict of metrics {name: (value, warn, crit, min, max)}
    """
    status_text = {OK: "OK", WARNING: "WARNING", CRITICAL: "CRITICAL", UNKNOWN: "UNKNOWN"}
    
    output = f"{status_text.get(status, 'UNKNOWN')} - {message}"
    
    if perfdata:
        perf_strings = []
        for name, values in perfdata.items():
            if isinstance(values, tuple):
                value, warn, crit, min_val, max_val = values + (None,) * (5 - len(values))
                perf_str = f"{name}={value}"
                if warn is not None:
                    perf_str += f";{warn}"
                if crit is not None:
                    perf_str += f";{crit}"
                if min_val is not None:
                    perf_str += f";{min_val}"
                if max_val is not None:
                    perf_str += f";{max_val}"
            else:
                perf_str = f"{name}={values}"
            perf_strings.append(perf_str)
        
        output += " | " + " ".join(perf_strings)
    
    print(output)
    sys.exit(status)


def check_thresholds(
    value: float,
    warning: Optional[float],
    critical: Optional[float],
    lower_is_worse: bool = False,
) -> int:
    """
    Check value against thresholds.
    
    Args:
        value: Current value
        warning: Warning threshold
        critical: Critical threshold
        lower_is_worse: If True, lower values are worse (default: higher is worse)
    
    Returns:
        Status code (OK, WARNING, CRITICAL)
    """
    if lower_is_worse:
        if critical is not None and value <= critical:
            return CRITICAL
        if warning is not None and value <= warning:
            return WARNING
    else:
        if critical is not None and value >= critical:
            return CRITICAL
        if warning is not None and value >= warning:
            return WARNING
    return OK


# =============================================================================
# CHECK IMPLEMENTATION
# =============================================================================

def check_tcp_service(
    host: str,
    port: int,
    timeout: float = 10.0,
    warning: float = 1.0,
    critical: float = 5.0,
    send_string: Optional[str] = None,
    expect_string: Optional[str] = None,
) -> Tuple[int, str, dict]:
    """
    Check TCP service availability and response time.
    
    Returns:
        Tuple of (status, message, perfdata)
    """
    start_time = time.time()
    
    try:
        # Create socket and connect
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        
        # Optional: send data
        if send_string:
            sock.send(send_string.encode())
        
        # Optional: receive and check response
        if expect_string:
            response = sock.recv(4096).decode(errors="ignore")
            if expect_string not in response:
                sock.close()
                return (
                    CRITICAL,
                    f"Expected string '{expect_string}' not found in response",
                    {"response_time": (time.time() - start_time, warning, critical, 0)},
                )
        
        sock.close()
        response_time = time.time() - start_time
        
        # Check thresholds
        status = check_thresholds(response_time, warning, critical)
        
        perfdata = {
            "response_time": (f"{response_time:.4f}s", warning, critical, 0),
        }
        
        if status == CRITICAL:
            message = f"Response time {response_time:.3f}s exceeds critical threshold"
        elif status == WARNING:
            message = f"Response time {response_time:.3f}s exceeds warning threshold"
        else:
            message = f"Port {port} open, response time {response_time:.3f}s"
        
        return status, message, perfdata
        
    except socket.timeout:
        return (
            CRITICAL,
            f"Connection timeout after {timeout}s",
            {"response_time": (timeout, warning, critical, 0)},
        )
    except socket.error as e:
        return CRITICAL, f"Connection failed: {e}", {}
    except Exception as e:
        return UNKNOWN, f"Unexpected error: {e}", {}


def check_http_service(
    host: str,
    port: int = 80,
    path: str = "/",
    ssl: bool = False,
    timeout: float = 10.0,
    warning: float = 1.0,
    critical: float = 5.0,
    expected_code: int = 200,
) -> Tuple[int, str, dict]:
    """
    Check HTTP service availability.
    
    Returns:
        Tuple of (status, message, perfdata)
    """
    import urllib.request
    import urllib.error
    
    protocol = "https" if ssl else "http"
    url = f"{protocol}://{host}:{port}{path}"
    
    start_time = time.time()
    
    try:
        request = urllib.request.Request(url)
        request.add_header("User-Agent", "CheckMK Active Check")
        
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_time = time.time() - start_time
            http_code = response.getcode()
            content_length = len(response.read())
        
        perfdata = {
            "response_time": (f"{response_time:.4f}s", warning, critical, 0),
            "size": (content_length, None, None, 0),
        }
        
        # Check HTTP code
        if http_code != expected_code:
            return (
                CRITICAL if http_code >= 500 else WARNING,
                f"HTTP {http_code} (expected {expected_code})",
                perfdata,
            )
        
        # Check response time
        status = check_thresholds(response_time, warning, critical)
        
        if status == CRITICAL:
            message = f"HTTP {http_code}, response time {response_time:.3f}s exceeds critical"
        elif status == WARNING:
            message = f"HTTP {http_code}, response time {response_time:.3f}s exceeds warning"
        else:
            message = f"HTTP {http_code}, response time {response_time:.3f}s, {content_length} bytes"
        
        return status, message, perfdata
        
    except urllib.error.HTTPError as e:
        return CRITICAL, f"HTTP {e.code}: {e.reason}", {}
    except urllib.error.URLError as e:
        return CRITICAL, f"Connection failed: {e.reason}", {}
    except socket.timeout:
        return CRITICAL, f"Timeout after {timeout}s", {}
    except Exception as e:
        return UNKNOWN, f"Error: {e}", {}


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Check TCP/HTTP service availability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    check_myservice -H example.com -p 443
    check_myservice -H example.com -p 80 --http
    check_myservice -H example.com -p 443 --http --ssl -w 2 -c 5
        """,
    )
    
    # Required arguments
    parser.add_argument(
        "-H", "--host",
        required=True,
        help="Host name or IP address",
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        required=True,
        help="Port number",
    )
    
    # Optional arguments
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=10.0,
        help="Connection timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "-w", "--warning",
        type=float,
        default=1.0,
        help="Warning threshold for response time in seconds (default: 1.0)",
    )
    parser.add_argument(
        "-c", "--critical",
        type=float,
        default=5.0,
        help="Critical threshold for response time in seconds (default: 5.0)",
    )
    
    # HTTP-specific options
    parser.add_argument(
        "--http",
        action="store_true",
        help="Perform HTTP check instead of TCP",
    )
    parser.add_argument(
        "--ssl",
        action="store_true",
        help="Use HTTPS (requires --http)",
    )
    parser.add_argument(
        "--path",
        default="/",
        help="URL path for HTTP check (default: /)",
    )
    parser.add_argument(
        "--expected-code",
        type=int,
        default=200,
        help="Expected HTTP status code (default: 200)",
    )
    
    # TCP-specific options
    parser.add_argument(
        "--send",
        help="String to send after connect (TCP mode)",
    )
    parser.add_argument(
        "--expect",
        help="String to expect in response (TCP mode)",
    )
    
    args = parser.parse_args()
    
    # Perform check
    if args.http:
        status, message, perfdata = check_http_service(
            host=args.host,
            port=args.port,
            path=args.path,
            ssl=args.ssl,
            timeout=args.timeout,
            warning=args.warning,
            critical=args.critical,
            expected_code=args.expected_code,
        )
    else:
        status, message, perfdata = check_tcp_service(
            host=args.host,
            port=args.port,
            timeout=args.timeout,
            warning=args.warning,
            critical=args.critical,
            send_string=args.send,
            expect_string=args.expect,
        )
    
    output_result(status, message, perfdata)


if __name__ == "__main__":
    main()
