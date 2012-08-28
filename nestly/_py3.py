"""
Utilities for dealing with python3
"""

import itertools
import sys

py3 = sys.version_info[0] == 3

if py3:
    imap = map
else:
    imap = itertools.imap

def is_string(s):
    if py3:
        b = str
    else:
        b = basestring
    return isinstance(s, b)
