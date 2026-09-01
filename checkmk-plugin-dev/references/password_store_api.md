# Password Store API

> **CheckMK 2.5+, unstable**: `cmk.password_store.v1_unstable` is a work-in-progress API and may change before it stabilizes (planned for 2.6, per Werk #18600). Mention this to the user before recommending it for production plugins. No 2.4 equivalent — 2.4 plugins get secrets from the ruleset `Password` form spec and `.unsafe()` instead (see `special_agents.md`, `active_checks.md`).

## Purpose

Gives server-side programs (special agents, active checks) a supported way to resolve a secret that the user configured either directly or as a reference into CheckMK's encrypted password store — without ever printing the plaintext value accidentally (e.g. in logs, tracebacks).

## Core Components

| Name | Kind | Purpose |
|---|---|---|
| `Secret` | Class | Wraps a resolved secret. Masks its value on `repr()`/`str()`; call `.reveal()` to get the actual plaintext when you need it |
| `PasswordStoreError` | Exception | Raised when the store can't be read or a referenced entry doesn't exist |
| `parser_add_secret_option()` | Function | Adds a pair of mutually-exclusive `argparse` options: one for a directly-typed secret, one for a password-store reference |
| `resolve_secret_option()` | Function | Reads the parsed args and returns a `Secret`, regardless of which option the user picked |
| `dereference_secret()` | Function | Lower-level: resolves a secret directly from a `(store_id, file_path)` reference |
| `get_store_secret()` | Function | Internal use — reads the store's own master secret |

## Example: Special Agent Executable

```python
#!/usr/bin/env python3
import argparse
from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option

OPTION_NAME = "password"

parser = argparse.ArgumentParser()
parser_add_secret_option(
    parser,
    short="-p",
    long=f"--{OPTION_NAME}",
    help="Database password",
    required=True,
)
args = parser.parse_args()

secret = resolve_secret_option(args, OPTION_NAME)
password = secret.reveal()  # Only call reveal() where you actually need the plaintext
```

This lets a single `--password` CLI flag accept either a plaintext value (useful for manual debugging) or a password-store reference (what the GUI generates from a `Password` ruleset field), without the executable needing to know which.

## Best Practices

1. **Reveal late**: hold the `Secret` object as long as possible; call `.reveal()` only at the point of use (e.g. right before building an HTTP `Authorization` header).
2. **Don't log secrets**: `Secret.__repr__`/`__str__` are masked by design — don't work around that by logging `.reveal()` output.
3. **Treat it as unstable**: don't ship this in a plugin meant to run unmodified past the 2.6 stabilization without checking the changelog first.

## Related Topics

- **Server-side calls (`Password` form spec)** → `rulesets_api.md`, `special_agents.md` — how the secret gets from the GUI into the command line/stdin in the first place
- **Server-Side Programs API** → `server_side_programs_api.md` — other 2.5-only helpers for the same executables
