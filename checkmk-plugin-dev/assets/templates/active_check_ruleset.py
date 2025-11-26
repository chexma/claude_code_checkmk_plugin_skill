#!/usr/bin/env python3
"""
Active Check Ruleset Template
=============================
Location: ~/local/lib/python3/cmk_addons/plugins/<family>/rulesets/

This creates the GUI form for configuring the active check.
The rule appears under Setup > Services > <Topic>.

The variable name MUST start with "rule_spec_" prefix.
The "name" parameter must match the ActiveCheckConfig name.
"""

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    # Containers
    Dictionary,
    DictElement,
    List,
    Tuple,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    # Basic types
    String,
    Integer,
    Float,
    BooleanChoice,
    # Selection
    SingleChoice,
    SingleChoiceElement,
    # Special types
    Password,
    migrate_to_password,
    SimpleLevels,
    LevelDirection,
    # Defaults and validation
    DefaultValue,
    InputHint,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic


# =============================================================================
# SIMPLE ACTIVE CHECK RULESET
# =============================================================================

rule_spec_myservice = ActiveCheck(
    # Name must match ActiveCheckConfig name in server_side_calls
    name="myservice",
    
    # Title shown in rule list
    title=Title("My Custom Service Check"),
    
    # Topic determines where rule appears in Setup menu
    # Options: GENERAL, NETWORKING, APPLICATIONS, OPERATING_SYSTEM, 
    #          STORAGE, VIRTUALIZATION, CLOUD, ENVIRONMENTAL, PERIPHERALS
    topic=Topic.NETWORKING,
    
    # Help text shown at top of rule form
    help_text=Help(
        "This active check monitors TCP/HTTP services from the CheckMK server. "
        "It measures response time and checks service availability."
    ),
    
    # Parameter form definition
    parameter_form=lambda: Dictionary(
        title=Title("Check Configuration"),
        elements={
            # Service description
            "service_description": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Service description"),
                    help_text=Help(
                        "The name of the service in monitoring. "
                        "Leave empty to auto-generate based on host and port."
                    ),
                    custom_validate=(
                        validators.LengthInRange(min_value=1, max_value=80),
                    ),
                ),
            ),
            
            # Target host
            "host": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Hostname or IP address"),
                    help_text=Help(
                        "The host to check. Leave empty to use the monitored host's address."
                    ),
                ),
            ),
            
            # Port number
            "port": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Port number"),
                    prefill=DefaultValue(443),
                    custom_validate=(
                        validators.NumberInRange(min_value=1, max_value=65535),
                    ),
                ),
            ),
            
            # Connection timeout
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Connection timeout"),
                    help_text=Help("Timeout in seconds for the connection attempt."),
                    prefill=DefaultValue(10),
                    unit_symbol="seconds",
                    custom_validate=(
                        validators.NumberInRange(min_value=1, max_value=300),
                    ),
                ),
            ),
            
            # Response time thresholds using SimpleLevels
            "response_time": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Response time thresholds"),
                    help_text=Help(
                        "Set warning and critical thresholds for response time."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="seconds"),
                    prefill_fixed_levels=DefaultValue((1.0, 5.0)),
                ),
            ),
            
            # HTTP mode toggle
            "http_mode": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("HTTP mode"),
                    help_text=Help("Perform HTTP request instead of simple TCP connect."),
                    prefill=DefaultValue(False),
                ),
            ),
            
            # SSL toggle
            "use_ssl": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Use SSL/TLS"),
                    help_text=Help("Use HTTPS instead of HTTP (requires HTTP mode)."),
                    prefill=DefaultValue(False),
                ),
            ),
            
            # URL path for HTTP
            "path": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("URL path"),
                    help_text=Help("Path to request (default: /)"),
                    prefill=DefaultValue("/"),
                ),
            ),
            
            # Expected HTTP code
            "expected_code": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Expected HTTP status code"),
                    prefill=DefaultValue(200),
                    custom_validate=(
                        validators.NumberInRange(min_value=100, max_value=599),
                    ),
                ),
            ),
            
            # TCP mode: send string
            "send_string": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Send string (TCP mode)"),
                    help_text=Help("String to send after connection is established."),
                ),
            ),
            
            # TCP mode: expect string
            "expect_string": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Expected response (TCP mode)"),
                    help_text=Help("String expected in the response."),
                ),
            ),
        },
    ),
)


# =============================================================================
# ADVANCED EXAMPLE WITH CASCADING CHOICES
# =============================================================================

rule_spec_myservice_advanced = ActiveCheck(
    name="myservice_advanced",
    title=Title("Advanced Service Check"),
    topic=Topic.NETWORKING,
    parameter_form=lambda: Dictionary(
        elements={
            "service_description": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Service description"),
                    prefill=InputHint("My Service"),
                ),
            ),
            
            "host": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Target host"),
                    help_text=Help("Leave empty to use host address"),
                ),
            ),
            
            # Cascading choice for check mode
            "check_mode": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Check mode"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="tcp",
                            title=Title("TCP Port Check"),
                            parameter_form=Dictionary(
                                elements={
                                    "port": DictElement(
                                        required=True,
                                        parameter_form=Integer(
                                            title=Title("Port"),
                                            prefill=DefaultValue(22),
                                        ),
                                    ),
                                    "send": DictElement(
                                        required=False,
                                        parameter_form=String(
                                            title=Title("Send string"),
                                        ),
                                    ),
                                    "expect": DictElement(
                                        required=False,
                                        parameter_form=String(
                                            title=Title("Expect string"),
                                        ),
                                    ),
                                },
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="http",
                            title=Title("HTTP/HTTPS Check"),
                            parameter_form=Dictionary(
                                elements={
                                    "port": DictElement(
                                        required=False,
                                        parameter_form=Integer(
                                            title=Title("Port"),
                                            prefill=DefaultValue(443),
                                        ),
                                    ),
                                    "ssl": DictElement(
                                        required=False,
                                        parameter_form=BooleanChoice(
                                            title=Title("Use SSL"),
                                            prefill=DefaultValue(True),
                                        ),
                                    ),
                                    "path": DictElement(
                                        required=False,
                                        parameter_form=String(
                                            title=Title("URL path"),
                                            prefill=DefaultValue("/"),
                                        ),
                                    ),
                                    "expected_code": DictElement(
                                        required=False,
                                        parameter_form=SingleChoice(
                                            title=Title("Expected status"),
                                            elements=[
                                                SingleChoiceElement("200", Title("200 OK")),
                                                SingleChoiceElement("301", Title("301 Redirect")),
                                                SingleChoiceElement("302", Title("302 Redirect")),
                                                SingleChoiceElement("401", Title("401 Unauthorized")),
                                                SingleChoiceElement("403", Title("403 Forbidden")),
                                            ],
                                            prefill=DefaultValue("200"),
                                        ),
                                    ),
                                },
                            ),
                        ),
                    ],
                    prefill=DefaultValue("tcp"),
                ),
            ),
            
            # Common options
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Timeout (seconds)"),
                    prefill=DefaultValue(10),
                ),
            ),
            
            "response_time": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Response time levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="s"),
                    prefill_fixed_levels=DefaultValue((1.0, 5.0)),
                ),
            ),
        },
    ),
)


# =============================================================================
# EXAMPLE WITH AUTHENTICATION
# =============================================================================

rule_spec_myservice_auth = ActiveCheck(
    name="myservice_auth",
    title=Title("Authenticated Service Check"),
    topic=Topic.APPLICATIONS,
    parameter_form=lambda: Dictionary(
        elements={
            "service_description": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Service description"),
                ),
            ),
            
            "endpoint": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("API Endpoint URL"),
                    help_text=Help("Full URL including protocol"),
                    custom_validate=(
                        validators.MatchRegex(
                            regex=r"^https?://",
                            error_msg=Title("URL must start with http:// or https://"),
                        ),
                    ),
                ),
            ),
            
            "authentication": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    title=Title("Authentication"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="none",
                            title=Title("No authentication"),
                            parameter_form=Dictionary(elements={}),
                        ),
                        CascadingSingleChoiceElement(
                            name="basic",
                            title=Title("Basic Authentication"),
                            parameter_form=Dictionary(
                                elements={
                                    "username": DictElement(
                                        required=True,
                                        parameter_form=String(
                                            title=Title("Username"),
                                        ),
                                    ),
                                    "password": DictElement(
                                        required=True,
                                        parameter_form=Password(
                                            title=Title("Password"),
                                            migrate=migrate_to_password,
                                        ),
                                    ),
                                },
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="token",
                            title=Title("Bearer Token"),
                            parameter_form=Dictionary(
                                elements={
                                    "token": DictElement(
                                        required=True,
                                        parameter_form=Password(
                                            title=Title("API Token"),
                                            migrate=migrate_to_password,
                                        ),
                                    ),
                                },
                            ),
                        ),
                    ],
                    prefill=DefaultValue("none"),
                ),
            ),
            
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Timeout"),
                    prefill=DefaultValue(30),
                    unit_symbol="seconds",
                ),
            ),
        },
    ),
)


# =============================================================================
# EXAMPLE WITH MULTIPLE ENDPOINTS (List)
# =============================================================================

rule_spec_myservice_multi = ActiveCheck(
    name="myservice_multi",
    title=Title("Multi-Endpoint Service Check"),
    topic=Topic.NETWORKING,
    parameter_form=lambda: Dictionary(
        elements={
            "endpoints": DictElement(
                required=True,
                parameter_form=List(
                    title=Title("Endpoints to check"),
                    help_text=Help("Each endpoint creates a separate service"),
                    element_template=Dictionary(
                        elements={
                            "name": DictElement(
                                required=True,
                                parameter_form=String(
                                    title=Title("Service name suffix"),
                                ),
                            ),
                            "host": DictElement(
                                required=True,
                                parameter_form=String(
                                    title=Title("Host"),
                                ),
                            ),
                            "port": DictElement(
                                required=True,
                                parameter_form=Integer(
                                    title=Title("Port"),
                                    prefill=DefaultValue(443),
                                ),
                            ),
                        },
                    ),
                ),
            ),
            
            "common_timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Common timeout for all endpoints"),
                    prefill=DefaultValue(10),
                    unit_symbol="seconds",
                ),
            ),
        },
    ),
)
