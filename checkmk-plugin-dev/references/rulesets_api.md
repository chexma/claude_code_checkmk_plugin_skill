# Rulesets API V1 Reference

## Location
`~/local/lib/python3/cmk_addons/plugins/<family>/rulesets/`

## Complete Import Statement
```python
from cmk.rulesets.v1 import Title, Label, Help

from cmk.rulesets.v1.form_specs import (
    # Containers
    Dictionary,
    DictElement,
    List,
    # (no Tuple in v1 — use a Dictionary with required DictElements)
    
    # Basic types
    String,
    Integer,
    Float,
    BooleanChoice,
    
    # Selection
    SingleChoice,
    SingleChoiceElement,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    MultipleChoice,
    MultipleChoiceElement,
    
    # Specialized
    Password,
    migrate_to_password,
    SimpleLevels,
    Levels,
    LevelDirection,
    DefaultValue,
    InputHint,
    
    # Validators live in a submodule: validators.NumberInRange(...), validators.LengthInRange(...), ...
    validators,
)

from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    DiscoveryParameters,
    HostCondition,
    HostAndItemCondition,
    Topic,
    SpecialAgent,
    ActiveCheck,
)
```

## Rule Specification Types

### CheckParameters
For check plugin parameter configuration:

```python
rule_spec_mycheck = CheckParameters(
    name="mycheck",                           # Must match check_ruleset_name
    title=Title("My Check Parameters"),
    topic=Topic.GENERAL,
    parameter_form=_parameter_form,
    condition=HostAndItemCondition(           # Or HostCondition for no-item checks
        item_title=Title("Service name"),
    ),
)
```

### SpecialAgent
For special agent configuration:

```python
rule_spec_myagent = SpecialAgent(
    name="myagent",                           # Matches agent_myagent executable
    title=Title("My Special Agent"),
    topic=Topic.GENERAL,
    parameter_form=_parameter_form,
)
```

### All Rule Spec Types (`cmk.rulesets.v1.rule_specs`)
All take `name`, `title`, `topic`, `parameter_form` (callable returning a `Dictionary`), optional `help_text`, `is_deprecated`. Variable prefix is always `rule_spec_`.

| Class | Used for | Extra args |
|-------|----------|------------|
| `CheckParameters` | Check plugin params (`check_ruleset_name`) | `condition=HostCondition()` / `HostAndItemCondition(item_title=..., item_form=...)`, `create_enforced_service=True` |
| `DiscoveryParameters` | `discovery_ruleset_name` | — |
| `InventoryParameters` | Inventory plugin params | — |
| `EnforcedService` | Enforced service only (no check params rule) | `condition=...`; `parameter_form` may be `None` |
| `SpecialAgent` | Special agent (`server_side_calls`) | — |
| `ActiveCheck` | Active check (`server_side_calls`) | — |
| `AgentConfig` | Agent bakery config | — |
| `NotificationParameters` | Notification plugin params (discovered since 2.5, Werk #17884) | — |
| `SNMP`, `AgentAccess`, `Host` | Host-level config rules | `eval_type=EvalType.MERGE` or `EvalType.ALL` |
| `Service` | Generic service-level rule | `eval_type=...`, `condition=HostCondition()` / `HostAndServiceCondition()` |

`CheckParameters` automatically creates the matching "Enforced services" rule (`create_enforced_service=True`), so a separate `EnforcedService` is only needed for checks without a parameter ruleset.

### Topic Options
```python
Topic.APPLICATIONS
Topic.CACHING_MESSAGE_QUEUES
Topic.CLOUD
Topic.CONFIGURATION_DEPLOYMENT
Topic.DATABASES
Topic.ENVIRONMENTAL
Topic.GENERAL
Topic.LINUX
Topic.MIDDLEWARE
Topic.NETWORKING
Topic.NOTIFICATIONS
Topic.OPERATING_SYSTEM
Topic.PERIPHERALS
Topic.POWER
Topic.SERVER_HARDWARE
Topic.STORAGE
Topic.SYNTHETIC_MONITORING
Topic.VIRTUALIZATION   # fixed in 2.5 (Werk #17804): broke quicksearch before
Topic.WINDOWS

# Or a custom topic:
from cmk.rulesets.v1.rule_specs import CustomTopic
topic=CustomTopic(title=Title("My Vendor"))
```

## Form Specification Elements

### Dictionary (Container)
Main container for parameters:

```python
def _parameter_form():
    return Dictionary(
        title=Title("My Parameters"),
        help_text=Help("Configuration for my check"),
        elements={
            "param1": DictElement(
                required=True,
                parameter_form=String(title=Title("Parameter 1")),
            ),
            "param2": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Parameter 2"),
                    prefill=DefaultValue(10),
                ),
            ),
        },
    )
```

### SimpleLevels (Thresholds)
For warn/crit threshold configuration - integrates with check_levels():

```python
"levels_upper": DictElement(
    required=True,
    parameter_form=SimpleLevels(
        title=Title("Upper levels"),
        form_spec_template=Float(),
        level_direction=LevelDirection.UPPER,
        prefill_fixed_levels=DefaultValue(value=(80.0, 90.0)),
    ),
),

"levels_lower": DictElement(
    required=True,
    parameter_form=SimpleLevels(
        title=Title("Lower levels"),
        form_spec_template=Integer(),
        level_direction=LevelDirection.LOWER,
        prefill_fixed_levels=DefaultValue(value=(10, 5)),
    ),
),
```

### String
```python
String(
    title=Title("Hostname"),
    help_text=Help("Enter the target hostname"),
    prefill=DefaultValue("localhost"),
    custom_validate=[
        validators.LengthInRange(min_value=1, max_value=255),
        validators.MatchRegex(r"^[a-zA-Z0-9.-]+$"),
    ],
)
```

### Integer / Float
```python
Integer(
    title=Title("Port"),
    prefill=DefaultValue(8080),
    custom_validate=[validators.NumberInRange(min_value=1, max_value=65535)],
)

Float(
    title=Title("Threshold"),
    prefill=DefaultValue(50.0),
    unit_symbol="%",
)
```

### BooleanChoice
```python
BooleanChoice(
    title=Title("Enable feature"),
    prefill=DefaultValue(True),
    label=Label("Activate this feature"),
)
```

### SingleChoice (Dropdown)

> **IMPORTANT: `name=` must be a valid Python identifier, NOT a reserved keyword!**

```python
SingleChoice(
    title=Title("Protocol"),
    elements=[
        SingleChoiceElement(name="http", title=Title("HTTP")),
        SingleChoiceElement(name="https", title=Title("HTTPS")),
        SingleChoiceElement(name="tcp", title=Title("Raw TCP")),
    ],
    prefill=DefaultValue("https"),
)
```

#### SingleChoiceElement Naming Rules

The `name=` parameter must be a valid, non-reserved Python identifier:

```python
# BAD - These cause errors (Python reserved keywords)
SingleChoiceElement(name="True", title=Title("Enabled"))   # WRONG!
SingleChoiceElement(name="False", title=Title("Disabled")) # WRONG!
SingleChoiceElement(name="None", title=Title("Not set"))   # WRONG!

# GOOD - Use descriptive identifiers instead
SingleChoiceElement(name="enabled", title=Title("Enabled"))
SingleChoiceElement(name="disabled", title=Title("Disabled"))
SingleChoiceElement(name="not_set", title=Title("Not set"))
```

The `title=Title(...)` can display any text to the user - only `name=` has restrictions.

### CascadingSingleChoice (Conditional)
Shows different forms based on selection:

```python
CascadingSingleChoice(
    title=Title("Authentication"),
    elements=[
        CascadingSingleChoiceElement(
            name="none",
            title=Title("No authentication"),
            parameter_form=Dictionary(elements={}),
        ),
        CascadingSingleChoiceElement(
            name="basic",
            title=Title("Basic authentication"),
            parameter_form=Dictionary(
                elements={
                    "username": DictElement(
                        required=True,
                        parameter_form=String(title=Title("Username")),
                    ),
                    "password": DictElement(
                        required=True,
                        parameter_form=Password(
                            title=Title("Password"),
                            migrate=migrate_to_password,
                        ),
                    ),
                }
            ),
        ),
    ],
    prefill=DefaultValue("none"),
)
```

### Password
For credentials (integrates with password store):

```python
Password(
    title=Title("API Token"),
    migrate=migrate_to_password,  # only needed for rules created with the legacy ValueSpec format
)
```

The `Password` form spec supports the password store by itself. `migrate_to_password` only converts legacy stored values (`("password", x)` / `("store", id)`) into the new model. Keep it when you migrate an existing legacy ruleset; a brand-new ruleset doesn't need it.

### List
For multiple items:

```python
List(
    title=Title("Additional hosts"),
    element_template=String(title=Title("Hostname")),
    add_element_label=Label("Add host"),
    remove_element_label=Label("Remove"),
)
```

### No Tuple in v1
`cmk.rulesets.v1` has no `Tuple` form spec (importing it raises `ImportError`). Use a `Dictionary` with required `DictElement`s instead, or `SimpleLevels`/`Levels` for warn/crit pairs:

```python
Dictionary(
    title=Title("Port range"),
    elements={
        "from_port": DictElement(parameter_form=Integer(title=Title("From port")), required=True),
        "to_port": DictElement(parameter_form=Integer(title=Title("To port")), required=True),
    },
)
```

### Other Form Specs
All importable from `cmk.rulesets.v1.form_specs`; all accept `title`, `help_text`, `migrate`, `custom_validate`.

| Form spec | Value in params | Key args |
|-----------|--------------|----------|
| `FixedValue` | the fixed value | `value=`, `label=` |
| `ServiceState` | `0..3` | `prefill=DefaultValue(ServiceState.WARN)` (constants `OK/WARN/CRIT/UNKNOWN`) |
| `HostState` | `0..2` | `prefill=DefaultValue(HostState.DOWN)` (`UP/DOWN/UNREACH`) |
| `Percentage` | float | `prefill=`, `label=` |
| `DataSize` | int (bytes) | `displayed_magnitudes=[IECMagnitude.MEBI, ...]` or `[SIMagnitude.KILO, ...]` (required) |
| `TimeSpan` | float (seconds) | `displayed_magnitudes=[TimeMagnitude.MILLISECOND/SECOND/MINUTE/HOUR/DAY]` (required) |
| `MultilineText` | str | `monospaced=`, `macro_support=` |
| `RegularExpression` | str | `predefined_help_text=MatchingScope.PREFIX/INFIX/FULL` (required) |
| `FileUpload` | `(file_name, mime_type, content_bytes)` | `extensions=(".pem",)`, `mime_types=` |
| `Proxy` | proxy model | `allowed_schemas=`; `migrate=migrate_to_proxy` for legacy values |
| `TimePeriod` | time period name | `migrate=migrate_to_time_period` for legacy values |
| `MonitoredHost` | host name | — |
| `MonitoredService` | service name | — |
| `Metric` | metric name | — |
| `MultipleChoice` | list of names | `elements=[MultipleChoiceElement(name=, title=)]`, `show_toggle_all=` |

**Grouping dictionary elements:** `DictElement(..., group=DictGroup(title=Title("Connection")))` renders elements sharing the same `DictGroup` together.

```python
conn = DictGroup(title=Title("Connection"))
Dictionary(
    elements={
        "size": DictElement(parameter_form=DataSize(displayed_magnitudes=[IECMagnitude.MEBI, IECMagnitude.GIBI])),
        "state": DictElement(parameter_form=ServiceState(prefill=DefaultValue(ServiceState.WARN))),
        "pattern": DictElement(parameter_form=RegularExpression(predefined_help_text=MatchingScope.INFIX)),
        "proxy": DictElement(parameter_form=Proxy(migrate=migrate_to_proxy), group=conn),
        "port": DictElement(parameter_form=Integer(custom_validate=(validators.NetworkPort(),)), group=conn),
    },
)
```

### Levels with Predictive Levels
`Levels` = `SimpleLevels` + a predictive option (`LevelsType.NONE/FIXED/PREDICTIVE`). The value your check function receives is `("no_levels", None)`, `("fixed", (w, c))` or `("predictive", (reference_metric, predicted_value, (w, c)))` — pass it unchanged to `check_levels()`.

```python
Levels(
    title=Title("Packets per second"),
    form_spec_template=Integer(unit_symbol="1/s"),
    level_direction=LevelDirection.UPPER,
    prefill_fixed_levels=DefaultValue((100000, 200000)),
    predictive=PredictiveLevels(
        reference_metric="packets",                  # metric the prediction is based on
        prefill_abs_diff=DefaultValue((5000, 10000)),
    ),
    migrate=migrate_to_upper_integer_levels,
)
```

### Migration Helpers (legacy `(warn, crit)` tuples → new model)
Use as `migrate=` when converting an existing legacy ruleset whose stored rules are plain tuples. The levels helpers take an optional `scale` factor (e.g. `scale=100` for fraction → percent).

| Helper | Target form spec |
|--------|------------------|
| `migrate_to_float_simple_levels` / `migrate_to_integer_simple_levels` | `SimpleLevels` |
| `migrate_to_upper_float_levels` / `migrate_to_upper_integer_levels` | `Levels` (upper) |
| `migrate_to_lower_float_levels` / `migrate_to_lower_integer_levels` | `Levels` (lower) |
| `migrate_to_password`, `migrate_to_proxy`, `migrate_to_time_period` | `Password`, `Proxy`, `TimePeriod` |

Example: `migrate_to_float_simple_levels((80, 90))` → `("fixed", (80.0, 90.0))`.

### Validators (`from cmk.rulesets.v1.form_specs import validators`)
Pass as `custom_validate=(...)`. All accept an optional `error_msg=Message(...)` (`from cmk.rulesets.v1 import Message`).

| Validator | Checks |
|-----------|--------|
| `NumberInRange(min_value=, max_value=)` | numeric range |
| `LengthInRange(min_value=, max_value=)` | length of str/list |
| `MatchRegex(regex)` | string matches regex |
| `NetworkPort()` | integer in 0–65535 |
| `Url(protocols=[validators.UrlProtocol.HTTP, validators.UrlProtocol.HTTPS])` | URL with allowed scheme |
| `EmailAddress()` | email address |
| `RegexGroupsInRange(min_groups=, max_groups=)` | number of regex match groups |

## Complete Ruleset Example

```python
#!/usr/bin/env python3

from cmk.rulesets.v1 import Title, Label, Help
from cmk.rulesets.v1.form_specs import (
    Dictionary,
    DictElement,
    Float,
    Integer,
    SimpleLevels,
    LevelDirection,
    DefaultValue,
    BooleanChoice,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form():
    return Dictionary(
        title=Title("CPU Usage Monitoring"),
        help_text=Help("Configure thresholds for CPU monitoring"),
        elements={
            "levels_upper": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Upper CPU levels"),
                    form_spec_template=Float(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(80.0, 90.0)),
                ),
            ),
            "average_minutes": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Averaging period (minutes)"),
                    prefill=DefaultValue(5),
                ),
            ),
            "include_iowait": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Include I/O wait"),
                    prefill=DefaultValue(True),
                ),
            ),
            "core_selection": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Core selection"),
                    elements=[
                        SingleChoiceElement(name="all", title=Title("All cores")),
                        SingleChoiceElement(name="average", title=Title("Average only")),
                    ],
                    prefill=DefaultValue("all"),
                ),
            ),
        },
    )


rule_spec_cpu_usage = CheckParameters(
    name="cpu_usage",
    title=Title("CPU Usage"),
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_parameter_form,
    condition=HostAndItemCondition(
        item_title=Title("CPU core"),
    ),
)
```

## Accessing Parameters in Check Function

```python
def check_cpu(item, params, section):
    # Get levels (returns tuple or None)
    levels_upper = params.get("levels_upper")
    # levels_upper is ("fixed", (80.0, 90.0)), ("no_levels", None) or None
    
    # Simple values
    avg_minutes = params.get("average_minutes", 5)
    include_iowait = params.get("include_iowait", True)
    core_selection = params.get("core_selection", "all")
    
    # Use with check_levels
    yield from check_levels(
        cpu_percent,
        levels_upper=levels_upper,
        metric_name="cpu_usage",
        label="CPU",
        render_func=render.percent,
    )
```

## Restart Requirements

After creating or modifying ruleset files:
```bash
omd restart apache
```

To also refresh search index:
```bash
omd restart redis
```

## Linking Check Plugin to Ruleset

In the check plugin:
```python
check_plugin_mycheck = CheckPlugin(
    name="mycheck",
    # ...
    check_default_parameters={
        "levels_upper": ("fixed", (80.0, 90.0)),
        "average_minutes": 5,
    },
    check_ruleset_name="mycheck",  # Links to rule_spec with this name
)
```

## Factory Functions for DRY Rulesets

When multiple parameters share similar patterns, use factory functions to reduce duplication:

### Age/Time Levels Factory
```python
from cmk.rulesets.v1 import Title, Help
from cmk.rulesets.v1.form_specs import (
    SimpleLevels, LevelDirection, DefaultValue, TimeSpan, TimeMagnitude
)

def _age_levels(title: str, help_text: str, warn_days: float, crit_days: float) -> SimpleLevels:
    """Factory for age-based thresholds with day/hour display."""
    return SimpleLevels(
        title=Title(title),
        help_text=Help(help_text),
        form_spec_template=TimeSpan(
            displayed_magnitudes=[TimeMagnitude.DAY, TimeMagnitude.HOUR]
        ),
        level_direction=LevelDirection.UPPER,
        prefill_fixed_levels=DefaultValue(
            value=(warn_days * 86400.0, crit_days * 86400.0)
        ),
    )

# Usage in parameter_form:
"cert_age": DictElement(
    parameter_form=_age_levels(
        "Certificate age",
        "Alert when certificate is older than threshold",
        warn_days=30.0,
        crit_days=7.0
    ),
),
"backup_age": DictElement(
    parameter_form=_age_levels(
        "Backup age",
        "Alert when last backup exceeds threshold",
        warn_days=1.0,
        crit_days=3.0
    ),
),
```

### Service State Choice Factory
```python
from cmk.rulesets.v1 import Title, Help
from cmk.rulesets.v1.form_specs import SingleChoice, SingleChoiceElement, DefaultValue

def _service_state_choice(title: str, help_text: str = "") -> SingleChoice:
    """Factory for enabled/disabled service state choices."""
    return SingleChoice(
        title=Title(title),
        help_text=Help(help_text) if help_text else None,
        elements=[
            SingleChoiceElement(name="enabled", title=Title("Enabled")),
            SingleChoiceElement(name="disabled", title=Title("Disabled")),
        ],
        prefill=DefaultValue("enabled"),
    )

# Usage:
"monitoring_state": DictElement(
    parameter_form=_service_state_choice(
        "Monitoring state",
        "Enable or disable monitoring for this item"
    ),
),
```

### Percentage Levels Factory
```python
def _percent_levels(title: str, warn: float = 80.0, crit: float = 90.0) -> SimpleLevels:
    """Factory for percentage-based thresholds."""
    return SimpleLevels(
        title=Title(title),
        form_spec_template=Float(unit_symbol="%"),
        level_direction=LevelDirection.UPPER,
        prefill_fixed_levels=DefaultValue(value=(warn, crit)),
    )
```

**Benefits:**
- Consistent UI across similar parameters
- Single place to update defaults
- Reduces copy-paste errors
- Self-documenting parameter patterns

---

## Changes in 2.5

| Werk | Compat | Change |
|------|--------|--------|
| #17876 | yes | `custom_validate` on `SimpleLevels`/`Levels` is now actually executed (before, only validators on `form_spec_template` ran). |
| #18966 | **no** | `custom_validate` is now enforced for `BooleanChoice`, `CascadingSingleChoice`, `FixedValue`, `HostState`, `Metric`, `MonitoredHost`, `MonitoredService`, `Password`, `Proxy`, `ServiceState`, `TimePeriod`. Existing rules that violate a validator become invalid and must be fixed manually. |
| #17884 | **no** | `rule_spec_<name> = NotificationParameters(...)` is now discovered; `name` must match the notification script name. The legacy `notification_parameter_registry` is no longer supported. |
| #18965 | yes | A v1 ruleset with the same name as a shipped *legacy* ruleset, placed in `~/local/lib/python3/cmk/plugins/<family>/rulesets/`, takes precedence over it. |
| #19167 | yes | New form rendering for all v1 rulesets (e.g. multiple validation errors shown at once). |
| #17804 | yes | `Topic.VIRTUALIZATION` no longer breaks the quicksearch index. |

---

## Related Topics

- **Use params in check function** → `agent_based_api.md` (check_levels integration)
- **Special agent configuration** → `special_agents.md` (SpecialAgent rule spec)
- **Active check configuration** → `active_checks.md` (ActiveCheck rule spec)
- **Agent Bakery configuration** → `bakery_api.md` (AgentConfig rule spec)
- **Best practices** → `best_practices.md`
