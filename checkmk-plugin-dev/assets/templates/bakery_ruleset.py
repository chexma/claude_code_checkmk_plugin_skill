#!/usr/bin/env python3
# =============================================================================
# CheckMK AgentConfig Ruleset Template
# =============================================================================
#
# This template creates a ruleset for configuring agent plugins via the
# Agent Bakery. It uses AgentConfig instead of CheckParameters.
#
# Installation:
#   ~/local/lib/python3/cmk_addons/plugins/<family>/rulesets/agent_config.py
#
# Companion files:
#   1. Bakery plugin in ~/local/lib/check_mk/base/cee/plugins/bakery/
#   2. Agent plugins in ~/local/share/check_mk/agents/plugins/
#
# After installation:
#   - Restart Apache: omd restart apache
#   - Find rule in: Setup > Agents > Agent rules
#
# =============================================================================

from cmk.rulesets.v1 import Title, Label, Help
from cmk.rulesets.v1.form_specs import (
    Dictionary,
    DictElement,
    String,
    Integer,
    Float,
    BooleanChoice,
    Password,
    SingleChoice,
    SingleChoiceElement,
    TimeSpan,
    TimeMagnitude,
    DefaultValue,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _parameter_form_my_plugin():
    """
    Define the configuration form for the agent plugin.
    
    These parameters will be passed to the Bakery plugin's conf argument.
    """
    return Dictionary(
        title=Title("My Plugin Configuration"),
        help_text=Help(
            "Configure the my_plugin agent plugin. "
            "The plugin will be distributed to hosts matching this rule."
        ),
        elements={
            # -----------------------------------------------------------------
            # Connection Settings
            # -----------------------------------------------------------------
            "api_url": DictElement(
                parameter_form=String(
                    title=Title("API URL"),
                    help_text=Help("The URL of the API endpoint to query"),
                    prefill=DefaultValue("http://localhost:8080/api"),
                    custom_validate=(
                        validators.Url(
                            protocols=[validators.UrlProtocol.HTTP, validators.UrlProtocol.HTTPS]
                        ),
                    ),
                ),
                required=True,
            ),
            
            "username": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help("Username for API authentication"),
                ),
                required=True,
            ),
            
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Password"),
                    help_text=Help("Password for API authentication"),
                ),
            ),
            
            # -----------------------------------------------------------------
            # Execution Settings
            # -----------------------------------------------------------------
            "interval": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Execution interval"),
                    help_text=Help(
                        "How often the plugin should be executed. "
                        "Leave empty for synchronous execution on every agent run."
                    ),
                    label=Label("Run every"),
                    displayed_magnitudes=[
                        TimeMagnitude.SECOND,
                        TimeMagnitude.MINUTE,
                        TimeMagnitude.HOUR,
                    ],
                    prefill=DefaultValue(300.0),  # 5 minutes
                ),
            ),
            
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Title("Timeout"),
                    help_text=Help("Request timeout in seconds"),
                    label=Label("seconds"),
                    prefill=DefaultValue(30),
                    custom_validate=(
                        validators.NumberInRange(min_value=1, max_value=300),
                    ),
                ),
            ),
            
            # -----------------------------------------------------------------
            # SSL/TLS Settings
            # -----------------------------------------------------------------
            "verify_ssl": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Verify SSL certificate"),
                    help_text=Help(
                        "Whether to verify the SSL certificate of the API endpoint"
                    ),
                    label=Label("Verify SSL certificate"),
                    prefill=DefaultValue(True),
                ),
            ),
            
            # -----------------------------------------------------------------
            # Optional: Log Level Selection
            # -----------------------------------------------------------------
            "log_level": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Log level"),
                    help_text=Help("Verbosity of plugin logging"),
                    elements=[
                        SingleChoiceElement(name="debug", title=Title("Debug")),
                        SingleChoiceElement(name="info", title=Title("Info")),
                        SingleChoiceElement(name="warning", title=Title("Warning")),
                        SingleChoiceElement(name="error", title=Title("Error")),
                    ],
                    prefill=DefaultValue("info"),
                ),
            ),
            
            # -----------------------------------------------------------------
            # Optional: Numeric Threshold
            # -----------------------------------------------------------------
            "max_items": DictElement(
                parameter_form=Integer(
                    title=Title("Maximum items to collect"),
                    help_text=Help("Limit the number of items collected per run"),
                    prefill=DefaultValue(100),
                    custom_validate=(
                        validators.NumberInRange(min_value=1, max_value=10000),
                    ),
                ),
            ),
        },
    )


# =============================================================================
# Rule Registration
# =============================================================================

# The name must match the Bakery plugin's PLUGIN_NAME
rule_spec_my_plugin_bakery = AgentConfig(
    name="my_plugin",  # Must match bakery plugin name!
    title=Title("My Plugin"),
    topic=Topic.GENERAL,  # Or Topic.APPLICATIONS, Topic.OPERATING_SYSTEM, etc.
    parameter_form=_parameter_form_my_plugin,
)


# =============================================================================
# Minimal Example (Distribution Only)
# =============================================================================
#
# If you just want to distribute a plugin without configuration options:
#
# def _parameter_form_minimal():
#     return Dictionary(elements={})
#
# rule_spec_simple_plugin = AgentConfig(
#     name="simple_plugin",
#     title=Title("Simple Plugin"),
#     topic=Topic.GENERAL,
#     parameter_form=_parameter_form_minimal,
# )
