# Password Store API

> **CheckMK 2.5+, unstable**: `cmk.password_store.v1_unstable` is a work-in-progress API and may still change. It is expected to become stable in the next major release, 3.0.0; the legacy APIs (`cmk.special_agents.v0_unstable`, `cmk.utils.password_store`, bakery API v1) are deprecated in 3.0.0 and removed in 3.1.0 (Werk #18600, corrected by Werk #19370). Mention this to the user before recommending it for production plugins. No 2.4 equivalent — 2.4 plugins pass `params["password"].unsafe()` in `command_arguments` instead (see `special_agents.md`, `active_checks.md`).

## Purpose

Gives server-side programs (special agents, active checks) a supported way to resolve a secret that the user configured either directly or as a reference into CheckMK's encrypted password store — without ever printing the plaintext value accidentally (e.g. in logs, tracebacks).

## Core Components

| Name | Kind | Purpose |
|---|---|---|
| `Secret[T]` | Class | Wraps a resolved secret. `str()` gives `****`, `repr()` gives `Secret('****')`; call `.reveal()` to get the plaintext |
| `PasswordStoreError` | Exception (`RuntimeError`) | Raised when the store key/file can't be read or the referenced id doesn't exist |
| `parser_add_secret_option(parser, /, *, short=None, long, help, required)` | Function | Adds a mutually-exclusive `argparse` pair: `<long>` (plaintext, `type=Secret`) and `<long>-id` (password-store reference) |
| `resolve_secret_option(args, option_name) -> Secret[str]` | Function | Returns a `Secret` from whichever of the two options was given; raises `TypeError` if neither was |
| `dereference_secret(raw: str, /) -> Secret[str]` | Function | Lower-level: resolves a reference string `"<id>:<store_file>"` |
| `get_store_secret()` | Function | Internal — reads/creates the store's master key. Not for plugins |
| `PasswordStore` | Class | Internal — encrypts/decrypts the store file. Not for plugins |

## How the Secret Travels

1. Ruleset: a `Password` form spec (`rulesets_api.md`).
2. Server-side calls: `params["password"]` is a `cmk.server_side_calls.v1.Secret`. Put it **into `command_arguments`** as-is:
   ```python
   args.extend(["--password-id", params["password"]])
   ```
   CheckMK renders it as `<id>:<store_file>` — the plaintext never appears on the command line. (A `Secret` cannot be used for `stdin=` or environment variables; both only take `str`.)
3. Executable: `parser_add_secret_option` + `resolve_secret_option` (below).

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
# -> usage: (-p PASSWORD | --password-id PASSWORD_ID)
args = parser.parse_args()

secret = resolve_secret_option(args, OPTION_NAME)
password = secret.reveal()  # Only call reveal() where you actually need the plaintext
```

`--password` takes a plaintext value (useful for manual debugging, but visible in the process table); `--password-id` takes the store reference the server-side calls plugin generates. The executable doesn't need to care which one was used.

**Hyphenated option names** (e.g. `long="--api-token"`, `resolve_secret_option(args, "api-token")`) only work from **2.5.0p13** on (Werk #22275). For earlier 2.5 patch releases, use names without hyphens.

## Best Practices

1. **Reveal late**: hold the `Secret` object as long as possible; call `.reveal()` only at the point of use (e.g. right before building an HTTP `Authorization` header).
2. **Don't log secrets**: `Secret.__repr__`/`__str__` are masked by design — don't work around that by logging `.reveal()` output.
3. **Use `--<name>-id` in the server-side calls plugin**, never the plaintext option.
4. **Treat it as unstable**: check the changelog before relying on it beyond 2.5 (stabilization expected in 3.0.0).
5. **Supporting 2.4 too**: wrap the import in `try/except ImportError` and fall back to a plain `--password` option; the 2.4 SSC must then pass `params["password"].unsafe()` (see `assets/templates/active_check_executable.py`).

## Related Topics

- **Server-side calls (`Password` form spec)** → `rulesets_api.md`, `special_agents.md` — how the secret gets from the GUI into the command line in the first place
- **Server-Side Programs API** → `server_side_programs_api.md` — other 2.5-only helpers for the same executables
