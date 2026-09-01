# Server-Side Programs API

> **CheckMK 2.5+, unstable**: `cmk.server_side_programs.v1_unstable` is a work-in-progress API and may change before it stabilizes (planned for 2.6, per Werk #18600). Mention this to the user before recommending it for production plugins. No 2.4 equivalent — these are convenience utilities layered on top of the existing special agent / active check executables described in `special_agents.md` and `active_checks.md`.

## Purpose

Convenience utilities for the executables that run on the CheckMK server (special agents, active checks): crash reporting, request tracing for debugging, per-host persistent state, and safer TLS handling when connecting by IP.

## Core Components

### `report_agent_crashes(name, version)` — decorator factory

Wraps your `main()` so unhandled exceptions produce a CheckMK crash report (visible in **Setup > Maintenance > Crash reports**) instead of a bare traceback on stderr.

```python
from cmk.server_side_programs.v1_unstable import report_agent_crashes

@report_agent_crashes("smith", "1.0.0")
def main() -> int:
    ...
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

### `Storage` — persistent key/value state between runs

Namespaced by program name and hostname, so state doesn't leak across hosts or plugins.

```python
from cmk.server_side_programs.v1_unstable import Storage

storage = Storage(program="myagent", hostname=host_config.name)
last_token = storage.read("auth_token", default=None)
...
storage.write("auth_token", new_token)
storage.unset("stale_key")
```

Use this for things like a cached OAuth token or a cursor/offset into a paginated API — data that should survive between check cycles but doesn't belong in the password store or the ruleset.

### `HostnameValidationAdapter` — TLS by IP, validated against a hostname

A `requests` HTTP adapter for the common case of connecting to a server by IP address while still validating the certificate against its real hostname (SNI).

```python
import requests
from cmk.server_side_programs.v1_unstable import HostnameValidationAdapter

session = requests.Session()
session.mount(
    "https://192.0.2.10",
    HostnameValidationAdapter(hostname="api.example.com"),
)
response = session.get("https://192.0.2.10/status")
```

### `vcrtrace()` — request recording for debugging

Returns an `argparse.Action` you add to your parser; enables recording/replaying HTTP traffic to reproduce issues without hitting the real endpoint each time.

```python
parser.add_argument("--vcrtrace", action=vcrtrace())
```

## Best Practices

1. **Wrap `main()` early**: apply `report_agent_crashes` at the outermost level so it catches everything, including argument-parsing bugs in your own code (not `argparse`'s own `SystemExit`).
2. **Namespace `Storage` state tightly**: use specific keys (`"oauth_token"`, not `"state"`) — the store is per-host but shared across all keys your plugin writes.
3. **Prefer `HostnameValidationAdapter` over disabling verification**: it keeps certificate validation on instead of the common (insecure) `verify=False` workaround — see the SSL gotchas in `special_agents.md`.
4. **Treat it as unstable**: don't ship this in a plugin meant to run unmodified past the 2.6 stabilization without checking the changelog first.

## Related Topics

- **Special agent executables** → `special_agents.md` — where `report_agent_crashes` and `Storage` are typically used
- **Active check executables** → `active_checks.md`
- **Password Store API** → `password_store_api.md` — the other new 2.5-only helper for these same executables
