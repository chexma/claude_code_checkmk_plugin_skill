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
    Tuple,
    
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
    
    # Validators
    NumberInRange,
    LengthInRange,
    MatchRegex,
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

### Topic Options
```python
Topic.GENERAL           # General / Various
Topic.APPLICATIONS      # Applications
Topic.CLOUD             # Cloud
Topic.DATABASES         # Databases
Topic.ENVIRONMENTAL     # Environmental
Topic.NETWORKING        # Networking
Topic.OPERATING_SYSTEM  # Operating System
Topic.STORAGE           # Storage
Topic.VIRTUALIZATION    # Virtualization
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
        LengthInRange(min_value=1, max_value=255),
        MatchRegex(r"^[a-zA-Z0-9.-]+$"),
    ],
)
```

### Integer / Float
```python
Integer(
    title=Title("Port"),
    prefill=DefaultValue(8080),
    custom_validate=[NumberInRange(min_value=1, max_value=65535)],
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
    migrate=migrate_to_password,  # Required for password store
)
```

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

### Tuple
For fixed-length sequences:

```python
Tuple(
    title=Title("Port range"),
    elements=[
        Integer(title=Title("From port")),
        Integer(title=Title("To port")),
    ],
)
```

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
    # levels_upper is ("fixed", (80.0, 90.0)) or None
    
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

## Related Topics

- **Use params in check function** → `agent_based_api.md` (check_levels integration)
- **Special agent configuration** → `special_agents.md` (SpecialAgent rule spec)
- **Active check configuration** → `active_checks.md` (ActiveCheck rule spec)
- **Agent Bakery configuration** → `bakery_api.md` (AgentConfig rule spec)
- **Best practices** → `best_practices.md`
