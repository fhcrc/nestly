"""SCons integration for nestly."""
from collections import OrderedDict
import json
import logging
import copy
import os

from . import core

try:
    import SCons.Node
    import SCons.Node.FS
    HAS_SCONS = True
except ImportError:
    import warnings
    warnings.warn('Unable to import SCons. Some functionality not available.')
    HAS_SCONS = False

logger = logging.getLogger('nestly.scons')

class SConsEncoder(json.JSONEncoder):
    """
    JSON Encoder which handles SCons objects.
    """
    def default(self, obj):
        if isinstance(obj, SCons.Node.NodeList):
            return list(obj)
        elif isinstance(obj, (SCons.Node.FS.Entry, SCons.Node.FS.File)):
            return str(obj)
        return super(SConsEncoder, self).default(obj)

def _create_control_file(source, target, env):
    target = str(target[0])
    with open(target, 'w') as fp:
        json.dump(env['control_dict'], fp, indent=2, cls=env['encoder_cls'])

def name_targets(func):
    """
    Wrap a function such that returning ``'a', 'b', 'c', [1, 2, 3]`` transforms
    the value into ``dict(a=1, b=2, c=3)``.

    This is useful in the case where the last parameter is an SCons command.
    """
    def wrap(*a, **kw):
        ret = func(*a, **kw)
        return dict(zip(ret[:-1], ret[-1]))
    return wrap


class SConsWrap(object):
    """A Nest wrapper to add SCons integration.

    This class wraps a :class:`Nest <nestly.core.Nest>` in order to provide
    methods which are useful for using nestly with SCons.

    A Nest passed to SConsWrap must have been created with
    ``include_outdir=True``, which is the default.

    :param nest: A :class:`Nest <nestly.core.Nest>` object to wrap
    :param dest_dir: The base directory for all output directories.
    :param alias_environment: An optional SCons ``Environment`` object.
        If present, targets added via :meth:`SConsWrap.add_target` will include
        an alias using the nest key.
    """

    def __init__(self, nest, dest_dir='.', alias_environment=None):
        """Initialize an SConsWrap.

        Takes the Nest to operate on and the base directory for all output
        directories.
        """
        self.nest = nest
        self.dest_dir = dest_dir
        self.alias_environment = alias_environment
        self.checkpoints = OrderedDict()

    def __iter__(self):
        "Iterate over the current controls."
        return self.nest.iter(self.dest_dir)

    def add(self, name, nestable, **kw):
        """
        Adds a level to the nesting and creates a checkpoint that can be
        reverted to later for aggregation by calling :meth:`SConsWrap.pop`.

        :param name: Identifier for the nest level
        :param nestable: A nestable object - see
            :meth:`Nest.add() <nestly.core.Nest.add>`.
        :param kw: Additional parameters to pass to
            :meth:`Nest.add() <nestly.core.Nest.add>`.
        """
        if core._is_iter(nestable):
            self.checkpoints[name] = self.nest
            self.nest = copy.copy(self.nest)
        return self.nest.add(name, nestable, **kw)

    def pop(self, name=None):
        """
        Reverts to the nest stage just before the corresponding call of
        :meth:`SConsWrap.add_aggregate`.  However, any aggregate collections
        which have been worked on will still be accessible, and can be called
        operated on together after calling this method.  If no name is passed,
        will revert to the last nest level.

        :param name: Name of the nest level to pop.
        """
        if name is not None:
            self.nest = self.checkpoints[name]
            keys = list(self.checkpoints.keys())
            name_idx = keys.index(name)
            assert name_idx >= 0

            # Pop every key from ``name`` on:
            for k in reversed(keys[name_idx:]):
                self.checkpoints.pop(k)
        else:
            self.nest = self.checkpoints.popitem()[1]

    def add_nest(self, name=None, **kw):
        """A simple decorator which wraps :meth:`nestly.core.Nest.add`."""
        def deco(func):
            self.add(name or func.__name__, func, **kw)
            return func
        return deco

    def _register_alias(self, key):
        if self.alias_environment:
            values = [c[key] for _, c in self if c[key]]
            values = self.alias_environment.Flatten(values)
            if values:
                self.alias_environment.Alias(key, values)

    def add_target(self, name=None):
        """
        Add an SCons target to this nest.

        The function decorated will be immediately called with each of the
        output directories and current control dictionaries. Each result will
        be added to the respective control dictionary for later nests to
        access.

        :param name: Name for the target in the name (default: function name).
        """
        def deco(func):
            def nestfunc(control):
                destdir = os.path.join(self.dest_dir, control['OUTDIR'])
                return [func(destdir, control)]
            key = name or func.__name__
            self.nest.add(key, nestfunc, create_dir=False)
            self._register_alias(key)
            return func
        return deco

    def add_target_with_env(self, environment, name=None):
        """Add an SCons target to this nest, with an SCons Environment

        The function decorated will be immediately called with three arguments:

        * ``environment``: A clone of the SCons environment, with variables
          populated for all values in the control dictionary, plus a variable
          ``OUTDIR``.
        * ``outdir``: The output directory
        * ``control``: The control dictionary

        Each result will be added to the respective control dictionary for
        later nests to access.

        Differs from :meth:`SConsWrap.add_target` only by the addition of the
        ``Environment`` clone.
        """
        def deco(func):
            def nestfunc(control):
                env = environment.Clone()
                for k, v in control.items():
                    if k in env:
                        logger.warn("Overwriting previously bound value %s=%s",
                                    k, env[k])
                    env[k] = v
                destdir = os.path.join(self.dest_dir, control['OUTDIR'])
                env['OUTDIR'] = destdir
                return [func(env, destdir, control)]
            key = name or func.__name__
            self.nest.add(key, nestfunc, create_dir=False)
            self._register_alias(key)
            return func
        return deco

    def add_aggregate(self, name, data_fac):
        """
        Add an aggregate target to this nest.


        Since nests added after the aggregate can access the construct returned
        by the factory function value, it can be mutated to provide additional
        values for use when the decorated function is called.

        To do something with the aggregates, you must :meth:`SConsWrap.pop`
        nest levels created between addition of the aggregate and then can add
        any normal targets you would like which take advantage of the targets
        added to the data structure.

        :param name: Name for the target in the nest
        :param data_fac: a nullary factory function which will be called
            immediately for each of the current control dictionaries and stored
            in each dictionary with the given name as in
            :meth:`SConsWrap.add_target`.
        """
        @self.add_target(name)
        def wrap(outdir, c):
            return data_fac()

    def add_controls(self, env, target_name='control',
                     file_name='control.json',
                     encoder_cls=SConsEncoder):
        """
        Adds a target to build a control file at each of the current leaves.

        :param env: SCons Environment object
        :param target_name: Name for target in nest
        :param file_name: Name for output file.
        """
        if not HAS_SCONS:
            raise ImportError('SCons not available')

        @self.add_target(name=target_name)
        def control(outdir, c):
            return env.Command(os.path.join(outdir, file_name),
                               [],
                               action=_create_control_file,
                               control_dict=c,
                               encoder_cls=encoder_cls)
