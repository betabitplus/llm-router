Requirement maps
================

These diagrams are intentionally small. A diagram should answer one question at
one level of abstraction; the authoritative Sphinx-Needs graph remains richer
than any single human-facing view.

.. only:: not graphviz_available

   .. note::

      Diagram rendering is unavailable in this build environment. The headings
      below still describe the intended slices; use the requirement tables and
      linked needs for the authoritative graph.

Product overview
----------------

Start here for the whole product. This view stops at features on purpose.

.. only:: graphviz_available

   .. needflow:: Product overview
      :engine: graphviz
      :direction: left
      :filter: type in ["goal", "feature"]
      :link_types: derives
      :alt: Product goals and features

Product-area drill-down
-----------------------

Each view below adds product requirements for one goal only. Engineering
constraints, implementation slices, and individual tests are excluded to keep
these maps readable.

Routing reliability
~~~~~~~~~~~~~~~~~~~

.. only:: graphviz_available

   .. needflow:: Routing reliability
      :engine: graphviz
      :direction: left
      :root_id: GOAL_ROUTING_RELIABILITY
      :root_direction: incoming
      :root_depth: 2
      :filter: type in ["goal", "feature", "req"]
      :link_types: derives

Configuration predictability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. only:: graphviz_available

   .. needflow:: Configuration predictability
      :engine: graphviz
      :direction: left
      :root_id: GOAL_CONFIGURATION_PREDICTABILITY
      :root_direction: incoming
      :root_depth: 2
      :filter: type in ["goal", "feature", "req"]
      :link_types: derives

Provider portability
~~~~~~~~~~~~~~~~~~~~

.. only:: graphviz_available

   .. needflow:: Provider portability
      :engine: graphviz
      :direction: left
      :root_id: GOAL_PROVIDER_PORTABILITY
      :root_direction: incoming
      :root_depth: 2
      :filter: type in ["goal", "feature", "req"]
      :link_types: derives

Resilient execution
~~~~~~~~~~~~~~~~~~~

.. only:: graphviz_available

   .. needflow:: Resilient execution
      :engine: graphviz
      :direction: left
      :root_id: GOAL_RESILIENT_EXECUTION
      :root_direction: incoming
      :root_depth: 2
      :filter: type in ["goal", "feature", "req"]
      :link_types: derives

Rich input and output
~~~~~~~~~~~~~~~~~~~~~

.. only:: graphviz_available

   .. needflow:: Rich input and output
      :engine: graphviz
      :direction: left
      :root_id: GOAL_RICH_INPUT_OUTPUT
      :root_direction: incoming
      :root_depth: 2
      :filter: type in ["goal", "feature", "req"]
      :link_types: derives

Tool orchestration
~~~~~~~~~~~~~~~~~~

.. only:: graphviz_available

   .. needflow:: Tool orchestration
      :engine: graphviz
      :direction: left
      :root_id: GOAL_TOOL_ORCHESTRATION
      :root_direction: incoming
      :root_depth: 2
      :filter: type in ["goal", "feature", "req"]
      :link_types: derives

Session continuity
~~~~~~~~~~~~~~~~~~

.. only:: graphviz_available

   .. needflow:: Session continuity
      :engine: graphviz
      :direction: left
      :root_id: GOAL_SESSION_CONTINUITY
      :root_direction: incoming
      :root_depth: 2
      :filter: type in ["goal", "feature", "req"]
      :link_types: derives

Data safety
~~~~~~~~~~~

.. only:: graphviz_available

   .. needflow:: Data safety
      :engine: graphviz
      :direction: left
      :root_id: GOAL_DATA_SAFETY
      :root_direction: incoming
      :root_depth: 2
      :filter: type in ["goal", "feature", "req"]
      :link_types: derives

Developer usability
~~~~~~~~~~~~~~~~~~~

.. only:: graphviz_available

   .. needflow:: Developer usability
      :engine: graphviz
      :direction: left
      :root_id: GOAL_DEVELOPER_USABILITY
      :root_direction: incoming
      :root_depth: 2
      :filter: type in ["goal", "feature", "req"]
      :link_types: derives

Engineering constraints
-----------------------

``TREQ_*`` objects are implementation-facing constraints or architecture
invariants derived from product requirements. They are deliberately kept out of
the product maps above.

.. needtable::
   :columns: id;title;status;derives as "Parent requirement";required_evidence as "Required evidence"
   :filter: type == "treq"
   :style: table

For exact source markers and the complete provenance graph, use
:doc:`../traceability`. For test coverage, use :doc:`../verification`.
