"""SCons integration for nestly."""
from collections import OrderedDict
import logging
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
        self.aggregates = OrderedDict()

    def __iter__(self):
        "Iterate over the current controls."
        return self.nest.iter(self.dest_dir)

    def add(self, *a, **kw):
        "Call .add on the wrapped Nest."
        return self.nest.add(*a, **kw)

    def add_nest(self, name=None, **kw):
        "A simple decorator which wraps nest.add."
        def deco(func):
            self.nest.add(name or func.__name__, func, **kw)
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
                for k, v in control.iteritems():
                    if k in env:
                        logger.warn("Overwriting previously bound value %s=%s", k, env[k])
                    env[k] = v
                destdir = os.path.join(self.dest_dir, control['OUTDIR'])
                env['OUTDIR'] = destdir
                return [func(env, destdir, control)]
            self.nest.add(name or func.__name__, nestfunc, create_dir=False)
            return func
        return deco

    def add_aggregate(self, data_fac, name=None):
        """Add an aggregate target to this nest.

        The first argument is a nullary factory function which will be called
        immediately for each of the current control dictionaries and stored in
        each dictionary with the given name like in ``add_target``. After
        ``finalize_aggregate`` or ``finalize_all_aggregates`` are called, the
        decorated function will then be called in the same way as
        ``add_target``, except with an additional argument: the value which was
        returned by the factory function.

        Since nests added after the aggregate can access the factory function's
        value, it can be mutated to provide additional values for use when the
        decorated function is called.
        """
        def deco(func):
            agg_name = name or func.__name__
            finalizers = self.aggregates[agg_name] = []
            @self.add_target(agg_name)
            def wrap(outdir, c):
                data = data_fac()
                def finalize():
                    return func(outdir, c, data)
                finalizers.append(finalize)
                return data
            return wrap
        return deco

    def finalize_aggregate(self, aggregate):
        """Call the finalizers for one particular aggregate.

        Finalizing an aggregate this way means that it will not be finalized by
        any future calls to ``finalize_all_aggregates``.
        """
        for finalizer in self.aggregates.pop(aggregate):
            finalizer()

    def finalize_all_aggregates(self):
        """Call the finalizers for all defined aggregates.

        If any aggregates have been specifically finalized by
        ``finalize_aggregate``, they will not be finalized again. This function
        itself calls ``finalize_aggregate``; if ``finalize_all_aggregates`` is
        called twice, aggregates will not be finalized twice.

        Aggregates will be finalized in the same order in which they were
        defined.
        """
        for aggregate in list(self.aggregates):
            self.finalize_aggregate(aggregate)
