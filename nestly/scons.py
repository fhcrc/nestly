"""SCons integration for nestly."""
import logging
import copy
import core
import os

logger = logging.getLogger('nestly.scons')

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

    This class wraps a Nest in order to provide methods which are useful for
    using nestly with SCons.

    A Nest passed to SConsWrap must have been created with include_outdir=True,
    which is the default.
    """

    def __init__(self, nest, dest_dir='.'):
        """Initialize an SConsWrap.

        Takes the Nest to operate on and the base directory for all output
        directories.
        """
        self.nest = nest
        self.dest_dir = dest_dir
        self.checkpoints = dict()

    def __iter__(self):
        "Iterate over the current controls."
        return self.nest.iter(self.dest_dir)

    def add(self, name, nestable, **kw):
        """Adds a level to the nesting and creates a checkpoint that can be reverted
        to later for aggregation by calling `self.close(name)`."""
        if core._is_iter(nestable):
            self.checkpoints[name] = self.nest
            self.nest = copy.copy(self.nest)
        return self.nest.add(name, nestable, **kw)

    def close(self, name):
        """Reverts to the nest stage just before the corresponding call of `add_level`.
        However, any aggregate collections which have been worked on will still be
        accessible, and can be called operated on together after calling this method."""
        try:
            self.nest = self.checkpoints[name]
        except KeyError:
            raise ValueError("Don't have a checkpoint for level {0}".format(name))

    def add_nest(self, name=None, **kw):
        "A simple decorator which wraps nest.add."
        def deco(func):
            self.add(name or func.__name__, func, **kw)
            return func
        return deco

    def add_target(self, name=None):
        """Add an SCons target to this nest.

        The function decorated will be immediately called with each of the
        output directories and current control dictionaries. Each result will
        be added to the respective control dictionary for later nests to
        access.
        """
        def deco(func):
            def nestfunc(control):
                destdir = os.path.join(self.dest_dir, control['OUTDIR'])
                return [func(destdir, control)]
            self.nest.add(name or func.__name__, nestfunc, create_dir=False)
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
                        logger.warn("Overwriting previously bound value %s=%s", k, env[k])
                    env[k] = v
                destdir = os.path.join(self.dest_dir, control['OUTDIR'])
                env['OUTDIR'] = destdir
                return [func(env, destdir, control)]
            self.nest.add(name or func.__name__, nestfunc, create_dir=False)
            return func
        return deco

    def add_aggregate(self, name, data_fac):
        """Add an aggregate target to this nest.

        The second argument is a nullary factory function which will be called
        immediately for each of the current control dictionaries and stored in
        each dictionary with the given name like in ``add_target``. 

        Since nests added after the aggregate can access the construct returned by the
        factory function value, it can be mutated to provide additional values for
        use when the decorated function is called.

        To do something with the aggregates, you must close close nest levels created
        between addition of the aggregate and then can add any normal targets you would
        like which take advantage of the targets added to the data structure.
        """
        @self.add_target(name)
        def wrap(outdir, c):
            return data_fac()

