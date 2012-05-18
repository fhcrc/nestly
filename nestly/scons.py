"""SCons integration for nestly."""

class SConsWrap(object):
    """A Nest wrapper to add SCons integration.

    This class wraps a Nest in order to provide methods which are useful for
    using nestly with SCons.
    """

    def __init__(self, nest, dest_dir='.'):
        """Initialize an SConsWrap.

        Takes the Nest to operate on and the base directory for all output
        directories.
        """
        self.nest = nest
        self.dest_dir = dest_dir
        self.aggregates = []

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
            targets = [(control, func(dir, control))
                       for dir, control in self.nest.iter(self.dest_dir)]
            def nestfunc(control):
                return [next(target for c, target in targets if control == c)]
            self.nest.add(name or func.__name__, nestfunc, create_dir=False)
            return func
        return deco

    def add_aggregate(self, data_fac, name=None):
        """Add an aggregate target to this nest.

        The first argument is a nullary factory function which will be called
        immediately for each of the current control dictionaries and stored in
        each dictionary with the given name like in ``add_target``. After
        ``finalize_aggregates`` is called, the decorated function will then be
        called in the same way as ``add_target``, except with an additional
        argument: the value which was returned by the factory function.

        Since nests added after the aggregate can access the factory function's
        value, it can be mutated to provide additional values for use when the
        decorated function is called.
        """
        def deco(func):
            agg_name = name or func.__name__
            finalizers = []
            @self.add_target(agg_name)
            def wrap(outdir, c):
                data = data_fac()
                def finalize():
                    return func(outdir, c, data)
                finalizers.append(finalize)
                return data
            self.aggregates.append((agg_name, finalizers))
            return wrap
        return deco

    def finalize_aggregates(self):
        """
        Call all of the defined aggregate functions, as described in
        ``add_aggregate``.
        """
        for _, finalizers in self.aggregates:
            for finalizer in finalizers:
                finalizer()

