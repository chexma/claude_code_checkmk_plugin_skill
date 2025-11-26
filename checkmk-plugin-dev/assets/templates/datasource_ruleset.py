#!/usr/bin/env python3
"""
Ruleset configuration for MyCloud special agent.

Location: ~/local/lib/python3/cmk_addons/plugins/mycloud/rulesets/special_agent.py
"""

from cmk.rulesets.v1 import Title, Label, Help
from cmk.rulesets.v1.form_specs import (
    Dictionary,
    DictElement,
    String,
    Integer,
    Password,
    BooleanChoice,
    SingleChoice,
    SingleChoiceElement,
    DefaultValue,
    migrate_to_password,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form():
    """Define the parameter form for the special agent."""
    return Dictionary(
        title=Title("My Cloud Controller"),
        help_text=Help(
            "Configure monitoring of a cloud controller via its REST API. "
            "This agent collects cluster metrics, VM status, and node information. "
            "Piggyback data is generated for VMs and nodes."
        ),
        elements={
            # Connection
            "port": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("API Port"),
                    help_text=Help("TCP port of the REST API"),
                    prefill=DefaultValue(9440),
                    custom_validate=[
                        validators.NumberInRange(min_value=1, max_value=65535)
                    ],
                ),
            ),
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Connection timeout"),
                    help_text=Help("Timeout for API requests in seconds"),
                    prefill=DefaultValue(30),
                    custom_validate=[
                        validators.NumberInRange(min_value=1, max_value=300)
                    ],
                ),
            ),
            "verify_ssl": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Verify SSL certificate"),
                    label=Label("Verify SSL certificate of the API"),
                    prefill=DefaultValue(True),
                ),
            ),
            
            # Authentication
            "username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help("API username with read permissions"),
                    custom_validate=[
                        validators.LengthInRange(min_value=1)
                    ],
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password"),
                    help_text=Help("API password"),
                    migrate=migrate_to_password,
                ),
            ),
            
            # Data collection options
            "no_piggyback": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Disable piggyback"),
                    label=Label("Do not generate piggyback data for VMs and nodes"),
                    prefill=DefaultValue(False),
                    help_text=Help(
                        "By default, the agent creates piggyback data for each VM and node. "
                        "Enable this to only monitor the cluster itself."
                    ),
                ),
            ),
            "vm_filter": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("VM name filter"),
                    help_text=Help(
                        "Regular expression to filter VMs by name. "
                        "Only matching VMs will be monitored. Leave empty for all VMs."
                    ),
                ),
            ),
            
            # Debug
            "debug": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Enable debug output"),
                    label=Label("Write debug messages to stderr"),
                    prefill=DefaultValue(False),
                ),
            ),
        },
    )


# Variable name MUST start with rule_spec_
rule_spec_mycloud = SpecialAgent(
    name="mycloud",                     # Must match server_side_calls name
    title=Title("My Cloud Controller"),
    topic=Topic.CLOUD,                  # Appears under "Cloud" in Setup
    parameter_form=_parameter_form,
    help_text=Help(
        "This rule configures the special agent for monitoring cloud controllers. "
        "The agent uses the REST API to collect cluster, VM, and node information. "
        "VMs and nodes appear as separate hosts via piggyback mechanism."
    ),
)


# ============================================================================
# OPTIONAL: Check Parameters Ruleset
# ============================================================================
# If you need configurable thresholds for your checks, add a separate ruleset:

from cmk.rulesets.v1.form_specs import SimpleLevels, LevelDirection, InputHint
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition


def _check_parameters_form():
    """Parameters for the VM check."""
    return Dictionary(
        elements={
            "cpu_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("CPU usage levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="%"),
                    prefill_fixed_levels=InputHint((80, 90)),
                ),
            ),
            "memory_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Memory usage levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="%"),
                    prefill_fixed_levels=InputHint((80, 90)),
                ),
            ),
        },
    )


rule_spec_mycloud_vm_params = CheckParameters(
    name="mycloud_vm",
    title=Title("My Cloud VM Parameters"),
    topic=Topic.CLOUD,
    parameter_form=_check_parameters_form,
    condition=HostAndItemCondition(item_title=Title("VM Name")),
)
