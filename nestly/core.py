"""
This is nestly core
"""
import collections
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
        if e.errno != 13:
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
    Core nestly object

    :param control_name: Name JSON file to be created in each leaf
    :param indent: Indentation level in json file
    :param fail_on_clash: Error if a nest level attempts to overwrite a
        previous value
    :param warn_on_clash: Print a warning if a nest level attempts ot overwrite
        a previous value
    """
    def __init__(self, control_name="control.json", indent=2,
            fail_on_clash=False, warn_on_clash=True):
        self.control_name = control_name
        self.indent = indent
        self.fail_on_clash = fail_on_clash
        self.warn_on_clash = warn_on_clash
        self._levels = []

    def iter(self, root=''):
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
                yield os.path.join(root, *dirs), control

        return inner({}, self._levels[:])

    def build(self, root="runs"):
        """
        Build a nested directory structure

        :param root: Root directory for structure
        """

        for d, control in self.iter(root):
            _mkdirs(d)
            with open(os.path.join(d, self.control_name), 'w') as fp:
                json.dump(control, fp, indent=self.indent)
                # RJSON and some other tools like a trailing newline
                fp.write('\n')

    def add_level(self, name, nestable, create_dir=True, update=False,
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

