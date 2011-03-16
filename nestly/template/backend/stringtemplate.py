"""
Render using string.Template
"""

from string import Template


def render(template_string, control_dict):
    """
    Render the provided template string using control_dict
    """
    template = Template(template_string)
    return template.substitute(control_dict)
