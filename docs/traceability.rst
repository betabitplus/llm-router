Requirements traceability
=========================

Requirements are the engineering source of truth. Verification and implementation
evidence are linked into the same Sphinx-Needs graph.

Implementation evidence
-----------------------

Implementation markers live next to the code they justify::

   # @impl Short implementation title, IMPL_EXAMPLE, [REQ_EXAMPLE]

The marker creates an ``IMPL_*`` need with a source link and an ``implements``
edge to the referenced requirement. Requirements that request ``impl`` evidence
must have at least one such incoming edge.

.. src-trace::
   :project: python

Graph inventory
---------------

.. needtable::
   :columns: id;title;type;needs_artifacts
   :filter: type in ["goal", "feature", "req", "treq", "impl", "testcase"]
