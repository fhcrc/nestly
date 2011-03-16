"""
Render using string's format method.
"""

def render(template_string, control_dict):
    """
    Render the provided template string using control_dict
    """
    return template_string.format(**control_dict)
