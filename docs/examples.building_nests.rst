Building Nests
==============

Basic Nest
----------

From ``examples/basic_nest/make_nest.py``, this is a simple, combinatorial
example.

.. literalinclude:: ../examples/basic_nest/make_nest.py
   :language: python
   :linenos:

This example is then run with the ``../examples/basic_nest/run_example.sh`` script.

.. literalinclude:: ../examples/basic_nest/run_example.sh
   :language: sh
   :linenos:

``echo.sh`` is just the simple script that runs ``nestrun`` and aggregates the
results into an ``aggregate.csv`` file:

.. literalinclude:: ../examples/basic_nest/echo.sh
   :language: sh
   :linenos:

Meal
----

This is a bit more complicated, with lookups on previous values of the
control dictionary:

.. literalinclude:: ../examples/meal/meal_example.py
   :language: python
   :linenos:
