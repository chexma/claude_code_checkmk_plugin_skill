# Server-Side Programs API

> **CheckMK 2.5+, unstable**: `cmk.server_side_programs.v1_unstable` is a work-in-progress API and may still change. It is expected to become stable in the next major release, 3.0.0; the legacy APIs (`cmk.special_agents.v0_unstable`, `cmk.utils.password_store`, bakery API v1) are deprecated in 3.0.0 and removed in 3.1.0 (Werk #18600, corrected by Werk #19370). Mention this to the user before recommending it for production plugins. No 2.4 equivalent — these are convenience utilities layered on top of the existing special agent / active check executables described in `special_agents.md` and `active_checks.md`.

## Purpose

Convenience utilities for the executables that run on the CheckMK server (special agents, active checks): crash reporting, request tracing for debugging, per-host persistent state, and safer TLS handling when connecting by IP.

Exported names (`__all__`): `HostnameValidationAdapter`, `Storage`, `report_agent_crashes`, `vcrtrace`.

## Core Components

### `report_agent_crashes(name, version)` — decorator factory

Wraps your `main() -> int` so unhandled exceptions produce a CheckMK crash report (visible in **Setup > Maintenance > Crash reports**) instead of a bare traceback.

```python
from cmk.server_side_programs.v1_unstable import report_agent_crashes

@report_agent_crashes("smith", "1.0.0")
def main() -> int:
    ...
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

Behavior:
- Only active when CheckMK sets `SERVER_SIDE_PROGRAM_CRASHES_PATH` (i.e. when run by the site). Otherwise the decorator is a no-op, so manual runs show the normal traceback.
- On a crash it writes the traceback to stderr, stores the report (local variables with keys containing `token`/`secret`/`pass`/`key` are redacted), prints `Failed: … (Crash-ID: …)` and returns `1`.
- The module also contains `report_check_crashes(name, version)` for active checks. It is importable but **not** in `__all__` and not in the official API docs — treat it as unofficial.

### `Storage(program_ident, host)` — persistent key/value text between runs

Namespaced by program identifier and host name, so state doesn't leak across hosts or plugins.

```python
from cmk.server_side_programs.v1_unstable import Storage

storage = Storage("myagent", args.hostname)   # positional: program_ident, host
last_token = storage.read("auth_token", None)  # default is required
...
storage.write("auth_token", new_token)         # str only - serialize (e.g. json.dumps) yourself
storage.unset("stale_key")
```

- Requires `SERVER_SIDE_PROGRAM_STORAGE_PATH` (set by CheckMK); otherwise `RuntimeError` — e.g. on manual CLI runs outside the site environment.
- Keys are URL-quoted and used as file names; after quoting they must be ≤ 255 characters (`ValueError`).
- `read()` returns the default if the key is unknown or unreadable.

Use this for things like a cached OAuth token or a cursor/offset into a paginated API — data that should survive between check cycles but doesn't belong in the password store or the ruleset.

### `HostnameValidationAdapter(hostname)` — TLS by IP, validated against a hostname

A `requests` HTTP adapter for connecting to a server by IP address while still validating the certificate against its real hostname. It also sets SNI and the `Host` header.

```python
import requests
from cmk.server_side_programs.v1_unstable import HostnameValidationAdapter

session = requests.Session()
session.mount("https://192.0.2.10", HostnameValidationAdapter("api.example.com"))
response = session.get("https://192.0.2.10/status")
```

### `vcrtrace(...)` — request recording for debugging

Returns an `argparse.Action` class you add to your parser; records HTTP traffic to a file on the first run and replays it on later runs (via `vcrpy`).

```python
from cmk.server_side_programs.v1_unstable import vcrtrace

parser.add_argument(
    "--vcrtrace",
    action=vcrtrace(filter_headers=[("authorization", "****")]),
)
```

- Keyword arguments: `filter_body`, `filter_query_parameters`, `filter_headers`, `filter_post_data_parameters` (passed to `vcr.VCR`) — use them to keep secrets out of trace files.
- The trace file must be inside `~/tmp/check_mk/debug/`, and the program must run in a TTY.

## Best Practices

1. **Wrap `main()` early**: apply `report_agent_crashes` at the outermost level so it catches everything, including argument-parsing bugs in your own code (not `argparse`'s own `SystemExit`).
2. **Namespace `Storage` state tightly**: use specific keys (`"oauth_token"`, not `"state"`) — the store is per-host but shared across all keys your plugin writes.
3. **Prefer `HostnameValidationAdapter` over disabling verification**: it keeps certificate validation on instead of the common (insecure) `verify=False` workaround — see the SSL gotchas in `special_agents.md`.
4. **Treat it as unstable**: check the changelog before relying on it beyond 2.5 (stabilization expected in 3.0.0).

## Related Topics

- **Special agent executables** → `special_agents.md` — where `report_agent_crashes` and `Storage` are typically used
- **Active check executables** → `active_checks.md`
- **Password Store API** → `password_store_api.md` — the other new 2.5-only helper for these same executables
