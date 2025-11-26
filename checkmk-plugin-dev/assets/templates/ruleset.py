#!/usr/bin/env python3
"""
Ruleset Definition Template
===========================
Location: ~/local/lib/python3/cmk_addons/plugins/<family>/rulesets/

This creates a rule for configuring check parameters.
After changes: omd restart apache
"""

from cmk.rulesets.v1 import Title, Label, Help
from cmk.rulesets.v1.form_specs import (
    Dictionary,
    DictElement,
    String,
    Integer,
    Float,
    BooleanChoice,
    SimpleLevels,
    LevelDirection,
    DefaultValue,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostAndItemCondition,
    HostCondition,
    Topic,
)


def _parameter_form():
    """Define the parameter form for the ruleset."""
    return Dictionary(
        title=Title("My Check Parameters"),
        help_text=Help("Configure thresholds and options for My Check"),
        elements={
            # Upper threshold levels (for check_levels)
            "levels_upper": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels"),
                    form_spec_template=Float(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(80.0, 90.0)),
                ),
            ),
            
            # Lower threshold levels (optional)
            "levels_lower": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels"),
                    form_spec_template=Float(),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue(value=(10.0, 5.0)),
                ),
            ),
            
            # Simple integer parameter
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Timeout (seconds)"),
                    prefill=DefaultValue(30),
                ),
            ),
            
            # Boolean option
            "include_details": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Include details in output"),
                    prefill=DefaultValue(True),
                    label=Label("Show extended information"),
                ),
            ),
            
            # Dropdown selection
            "mode": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Operating mode"),
                    elements=[
                        SingleChoiceElement(name="normal", title=Title("Normal")),
                        SingleChoiceElement(name="strict", title=Title("Strict")),
                        SingleChoiceElement(name="relaxed", title=Title("Relaxed")),
                    ],
                    prefill=DefaultValue("normal"),
                ),
            ),
        },
    )


# Register the ruleset
# Use HostAndItemCondition for checks with items (%s in service name)
# Use HostCondition for checks without items
rule_spec_mycheck = CheckParameters(
    name="mycheck",                             # Must match check_ruleset_name in CheckPlugin
    title=Title("My Check Parameters"),
    topic=Topic.GENERAL,                        # Category in Setup menu
    parameter_form=_parameter_form,
    condition=HostAndItemCondition(
        item_title=Title("Item name"),          # Label for item filter
    ),
    # For checks without items, use:
    # condition=HostCondition(),
)
