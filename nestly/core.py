"""
Core functions for building nests.
"""

import collections
import errno
import json
import os
import sys

def _mkdirs(d):
    """
    Make all directories up to d.

    No exception is raised if d exists.
    """
    try:
        os.makedirs(d)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise

_Nestable = collections.namedtuple('Nestable', ('name', 'nestable',
                                               'create_dir', 'update',
                                               'label_func'))

def _is_iter(iterable):
    """
    Returns whether an item is iterable or not
    """
    try:
        iter(iterable)
        return True
    except TypeError:
        return False

class Nest(object):
    """
    Nests are used to build nested parameter selections, culminating in a
    directory structure representing choices made, and a JSON dictionary with
    all selections.

    Build parameter combinations with :meth:`Nest.add`, then create a nested
    directory structure with :meth:`Nest.build`.

    :param control_name: Name JSON file to be created in each leaf
    :param indent: Indentation level in json file
    :param fail_on_clash: Error if a nest level attempts to overwrite a
        previous value
    :param warn_on_clash: Print a warning if a nest level attempts ot overwrite
        a previous value
    :param base_dict: Base dictionary to start all control dictionaries from
        (default: ``{}``)
    """
    def __init__(self, control_name="control.json", indent=2,
            fail_on_clash=False, warn_on_clash=True, base_dict=None):
        self.control_name = control_name
        self.indent = indent
        self.fail_on_clash = fail_on_clash
        self.warn_on_clash = warn_on_clash
        self._levels = []
        self.base_dict = base_dict or {}

    def iter(self, root=None):
        """
        Create an iterator of (directory, control_dict) tuples for all valid
        parameter choices in this :class:`Nest`.

        :param root: Root directory
        :rtype: Generator of ``(directory, control_dictionary)`` tuples.
        """
        def inner(control, nestables, dirs=None):
            #FIXME: This is messy
            if not dirs:
                dirs = []
            if nestables:
                # Still more nestables to consume...
                n = nestables[0]

                result = n.nestable(control)

                for r in result:
                    ctl = control.copy()
                    if n.update:
                        # Make sure expected key exists
                        if not n.name in r:
                            raise KeyError("Missing key for {0}".format(n.name))

                        # Check for collisions
                        u = frozenset(control.keys()) & frozenset(r.keys())
                        if u:
                            if self.fail_on_clash:
                                raise KeyError("Key overlap: {0}".format(u))
                            elif self.warn_on_clash:
                                #FIXME: Something better here
                                print >>sys.stderr, "Key overlap:", u
                        ctl.update(r)

                        # For directory making below
                        r = r[n.name]
                    else:
                        ctl[n.name] = r

                    new_dirs = (dirs + [n.label_func(r)] if n.create_dir
                                else dirs[:])
                    for d, c in inner(ctl, nestables[1:], new_dirs):
                        yield d, c
            else:
                # At leaf node
                yield os.path.join(root or '', *dirs), control

        return inner(self.base_dict, self._levels[:])

    def build(self, root="runs"):
        """
        Build a nested directory structure, starting in ``root``

        :param root: Root directory for structure
        """

        for d, control in self.iter(root):
            _mkdirs(d)
            with open(os.path.join(d, self.control_name), 'w') as fp:
                json.dump(control, fp, indent=self.indent)
                # RJSON and some other tools like a trailing newline
                fp.write('\n')

    def add(self, name, nestable, create_dir=True, update=False,
            label_func=str):
        """
        Add a level to the nest

        :param string name: Name of the level. Forms the key in the output
            dictionary.
        :param nestable: Either an iterable object containing values, _or_ a
            function which takes a single argument (the control dictionary)
            and returns an iterable object containing values
        :param boolean create_dir: Should a directory level be created for this
            nestable?
        :param boolean update: Should the control dictionary be updated with
            the results of each value returned by the nestable? Only valid for
            dictionary results; useful for updating multiple values. At a
            minimum, a key-value pair corresponding to ``name`` must be
            returned.
        :param label_func: Function to be called to convert each value to a
            directory label.
        """
        # Convert everything to functions
        if not callable(nestable):
            if not _is_iter(nestable):
                raise ValueError("Invalid nestable: " + str(nestable))
            old_nestable = nestable
            nestable = lambda _: old_nestable
        self._levels.append(_Nestable(name, nestable, create_dir, update,
                                      label_func))

