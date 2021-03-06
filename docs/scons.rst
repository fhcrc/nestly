=================
SCons integration
=================

.. py:currentmodule:: nestly.scons

SCons_ is an excellent build tool (analogous to ``make``). The
:mod:`nestly.scons` module is provided to make integrating nestly with SCons
easier. :class:`SConsWrap` wraps a :class:`~nestly.core.Nest` object to provide
additional methods for adding nests. SCons is complex and is fully documented
on their website, so we do not describe it here. However, for the purposes of
this document, it suffices to know that dependencies are created when a
*target* function is called.

The basic idea is that when writing an SConstruct file (analogous to a
Makefile), these :class:`SConsWrap` objects extend the usual nestly
functionality with build dependencies. Specifically, there are functions that
add targets to the nest. When SCons is invoked, these targets are identified
as dependencies and the needed code is run.

Typically, you will only need targets within some nest level to refer to things
either in the same nest, or in parent nests. However, it is possible to operate
on target collections which are not related in this way by using aggregate
targets.

Constructing an ``SConsWrap``
=============================

``SConsWrap`` objects wrap and modify a ``Nest`` object. Each ``Nest`` object
needs to have been created with ``include_outdir=True``, which is the default.

Optionally, a destination directory can be given to the ``SConsWrap`` which
will be passed to :meth:`Nest.iter() <nestly.core.Nest.iter>`::

    >>> nest = SConsWrap(Nest(), dest_dir='build')

In this example, all the nests created by ``nest`` will go under the ``build``
directory. Throughout the rest of this document, ``nest`` will refer to this
same :class:`SConsWrap` instance.

Adding levels
=============

Nest levels can still be added to the ``nest`` object::

    >>> nest.add('level1', ['spam', 'eggs'])

:class:`SConsWrap` also provides a convenience decorator
:meth:`SConsWrap.add_nest` for adding levels which use a function as their
nestable. The following examples are exactly equivalent::

    @nest.add_nest('level2', label_func=str.strip)
    def level2(c):
        return ['  __' + c['level1'], c['level1'] + '__  ']

    def level2(c):
        return ['  __' + c['level1'], c['level1'] + '__  ']
    nest.add('level2', level2, label_func=str.strip)

Another advantage to using the decorator is that the name parameter is
optional; if it's omitted, the name of the nest is taken from the name of the
function. As a result, the following example is also equivalent::

    @nest.add_nest(label_func=str.strip)
    def level2(c):
        return ['  __' + c['level1'], c['level1'] + '__  ']


.. note ::

  :meth:`~SConsWrap.add_nest` must always be called before being applied as a
  decorator. ``@nest.add_nest`` is not valid; the correct usage is
  ``@nest.add_nest()`` if no other parameters are specified.

Adding targets
==============

The fundamental action of SCons integration is in adding a target to a nest.
Adding a target is very much like adding a level in that it will add a key to
the control dictionary, except that it will not add any branching to a nest.
For example, successive calls to :meth:`Nest.add() <nestly.core.Nest.add>`
produces results like the following

.. testsetup:: n1,n2,n3,n4

    import pprint
    from nestly import Nest
    from nestly.scons import SConsWrap
    nest = SConsWrap(Nest())

.. doctest:: n1

    >>> nest.add('level1', ['A', 'B'])
    >>> nest.add('level2', ['C', 'D'])
    >>> pprint.pprint([c.items() for outdir, c in nest])
    [[('OUTDIR', 'A/C'), ('level1', 'A'), ('level2', 'C')],
     [('OUTDIR', 'A/D'), ('level1', 'A'), ('level2', 'D')],
     [('OUTDIR', 'B/C'), ('level1', 'B'), ('level2', 'C')],
     [('OUTDIR', 'B/D'), ('level1', 'B'), ('level2', 'D')]]

A crude illustration of how ``level1`` and ``level2`` relate::

    #               C .---- - -
    #    A .----------o level2
    #      |        D '---- - -
    # o----o level1
    #      |        C .---- - -
    #    B '----------o level2
    #               D '---- - -

Calling :meth:`~SConsWrap.add_target`, however, produces slightly different
results:

.. doctest:: n2

    >>> nest.add('level1', ['A', 'B'])
    >>> @nest.add_target()
    ... def target1(outdir, c):
    ...     return 't-{0[level1]}'.format(c)
    ...
    >>> pprint.pprint([c.items() for outdir, c in nest])
    [[('OUTDIR', 'A'), ('level1', 'A'), ('target1', 't-A')],
     [('OUTDIR', 'B'), ('level1', 'B'), ('target1', 't-B')]]

And a similar illustration of how ``level1`` and ``target1`` relate::

    #                t-A
    #    A .----------o------ - -
    # o----o level1      target1
    #    B '----------o------ - -
    #                t-B

:meth:`~SConsWrap.add_target` does not increase the total number of control
dictionaries from 2; it only updates each existing control dictionary to add
the ``target1`` key. This is effectively the same as calling
:meth:`~nestly.core.Nest.add` (or :meth:`~SConsWrap.add_nest`) with a function
and returning an iterable of one item:

.. doctest:: n3

    >>> nest.add('level1', ['A', 'B'])
    >>> @nest.add_nest()
    ... def target1(c):
    ...     return ['t-{0[level1]}'.format(c)]
    ...
    >>> pprint.pprint([c.items() for outdir, c in nest])
    [[('OUTDIR', 'A/t-A'), ('level1', 'A'), ('target1', 't-A')],
     [('OUTDIR', 'B/t-B'), ('level1', 'B'), ('target1', 't-B')]]

Astute readers might have noticed the key difference between the two: functions
decorated with :meth:`~SConsWrap.add_target` have an additional parameter,
``outdir``. This allows targets to be built into the correct place in the
directory hierarchy.

The other notable difference is that the function decorated by
:meth:`~SConsWrap.add_target` will be called exactly once with each control
dictionary. A function added with :meth:`~nestly.core.Nest.add` may be called
more than once with equal control dictionaries.

Like :meth:`~SConsWrap.add_nest`, :meth:`~SConsWrap.add_target` must always be
called, and optionally takes the name of the target as the first parameter. No
other parameters are accepted.

Adding aggregates
=================

As mentioned in the introduction, often you only need targets within a given nest level to depend on things in the same nest level or parental nest levels.
To get around this restriction, you can utilize nestly's aggregate functionality.

Adding an aggregate target creates a collection (for each terminal node of the current nest state) which can be updated in downstream nest levels.
Once targets have been added to the aggregate collection, you can return to a previous nest level by using the :meth:`~SConsWrap.pop` method and operate on the populated aggregate collection at that level.

For example, let's say we have two nest levels, ``level1`` and ``level2``, which take the values ``[A, B]`` and ``[C, D]`` respectively.
If we want to perform an operation for every unique combination of ``{level1, level2}``, then aggregate the results grouped by values of ``level1``:

.. doctest:: n4

    >>> # Create the first nest level, and add an aggregate named "aggregate1"
    >>> nest.add('level1', ['A', 'B'])
    >>> nest.add_aggregate('aggregate1', list)
    ...
    >>> # Next, add level2 and a target to level2
    >>> nest.add('level2', ['C', 'D'])
    >>> @nest.add_target()
    ... def some_target(outdir, c):
    ...     target = c['level1'] + c['level2']
    ...     # here we populate the aggregate
    ...     c['aggregate1'].append(target)
    ...     return target
    ...
    >>> # Now the aggregates have been filled!
    >>> # Note that the aggregate collection is shared among all descendents of
    >>> # each `level1` value
    >>> pprint.pprint([(c['level1'], c['level2'], c['aggregate1']) for outdir, c in nest])
    [('A', 'C', ['AC', 'AD']),
     ('A', 'D', ['AC', 'AD']),
     ('B', 'C', ['BC', 'BD']),
     ('B', 'D', ['BC', 'BD'])]
    >>>
    >>> # However, if we try to build something from the aggregate collection now, we'd get 4 copies (one for
    >>> # 'A/C', one for 'A/D', etc.).
    >>> # To return to the nest state prior to adding `level2`, we pop it from the nest:
    >>> nest.pop('level2')
    >>> # Now when we access the aggregate collection, there are only two entries, one for A and one for B:
    >>> pprint.pprint([(c['level1'], c['aggregate1']) for outdir, c in nest])
    [('A', ['AC', 'AD']), ('B', ['BC', 'BD'])]
    >>>
    >>> # we can add targets using the aggregate collection!
    >>> @nest.add_target()
    ... def operate_on_aggregate(outdir, c):
    ...     print 'agg', c['level1'], c['aggregate1']
    ...
    agg A ['AC', 'AD']
    agg B ['BC', 'BD']

As you can see above, aggregate targets are added using the :meth:`~SConsWrap.add_aggregate` method.
The first argument to this method is used as a key for accessing the aggregate collection(s) from the control dictionary.
The second argument should be a factory function which will be called with no arguments and set as the initial value of the aggregate (typically a collection constructor like `list` or `dict`).

Prior to using the aggregate collection, any branching nest levels added after the aggregate should be removed, using :meth:`~SConsWrap.pop` to prevent building identical targets.
This function, when passed the name of a nest level, returns the :class:`SConsWrap` to the state just before that nest level was created.
The only modifications which remain are those on the aggregate collection, which retains any targets added to it within the removed nest levels.
Once back at the parental nest level, targets added to the aggregate can be operated on by any further targets added.
Note that to pop a level from the nest, one must call :meth:`nestly.scons.SConsWrap.add` rather than :meth:`nestly.core.Nest.add`.

Because the results of operations on aggregates are just regular targets at some ancestral nest level, these targets can be used as the sources to targets further downstream.

.. note ::

  nestly's initial SCons aggregation functionality added in `version 0.4.0 <https://github.com/fhcrc/nestly/tree/0.4.0>`_ and described in the `nestly manuscript <http://dx.doi.org/doi:10.1093/bioinformatics/bts696>`_ involved registering aggregate functions before adding additional levels to the nest.
  This interface did not allow the user to utilize aggregate targets as sources of other targets downstream.
  The original aggregation functionality has since been removed in favor of that described above.

Calling commands from SCons
===========================

While the previous example demonstrate how to use the various methods of
:class:`SConsWrap`, they did not demonstrate how to actually call commands
using SCons. The easiest way is to define the various targets from within the
``SConstruct`` file::

    from nestly.scons import SConsWrap
    from nestly import Nest
    import os

    nest = Nest()
    wrap = SConsWrap(nest, 'build')

    # Add a nest for each of our input files.
    nest.add('input_file', [join('inputs', f) for f in os.listdir('inputs')],
             label_func=os.path.basename)

    # Each input will get transformed each of these different ways.
    nest.add('transformation', ['log', 'unit', 'asinh'])

    @nest.add_target()
    def transformed(outdir, c):
        # The template for the command to run.
        action = 'guppy mft --transform {0[transformation]} $SOURCE -o $TARGET'
        # Command will return a tuple of the targets; we want the only item.
        outfile, = Command(
            source=c['input_file'],
            target=os.path.join(outdir, 'transformed.jplace'),
            action=action.format(c))
        return outfile

A function :func:`name_targets` is also provided for more easily naming the
targets of an SCons command::

    @nest.add_target('target1')
    @name_targets
    def target1(outdir, c):
        return 'outfile1', 'outfile2', Command(
            source=c['input_file'],
            target=[os.path.join(outdir, 'outfile1'),
                    os.path.join(outdir, 'outfile2')],
            action="transform $SOURCE $TARGETS")

In this case, ``target1`` will be a dict resembling ``{'outfile1':
'build/outdir/outfile1', 'outfile2': 'build/outdir/outfile2'}``.

.. note ::

    :func:`name_targets` does not preserve the name of the decorated function,
    so the name of the target *must* be provided as a parameter to
    :meth:`~SConsWrap.add_target`.

A more involved, runnable example is in the ``examples/scons`` directory.

.. _Scons: http://scons.org/
