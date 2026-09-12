Whole-system intent map
=======================

Use this page to **reorient**, not to inspect every artifact. It deliberately stops at
Capabilities so the whole product remains readable. Pick a Goal or Capability node, then open
its product-area page from the :doc:`Intent map <index>` to continue down through
Requirements, Technical requirements, implementation, and executed verification.

.. only:: not graphviz_available

   .. note::

      Diagram rendering is unavailable in this build environment. Use the
      :doc:`Intent map <index>` to choose the same product branches.

.. only:: graphviz_available

   .. needflow:: Product intent overview
      :engine: graphviz
      :direction: down
      :filter: type in ["goal", "feature"]
      :link_types: derives
      :alt: Goals and their derived features

How to move through the map
---------------------------

The graph is intentionally only two levels deep:

**Goal → Capability**

Once you choose a branch, the product-area page adds the next levels progressively:

**Requirement → optional Technical requirement → implementation / executed test**

That keeps the global map useful as a map instead of turning it into a dense audit
report. For release blockers, start from :doc:`../specification-health`. For a dense
cross-graph forensic view, use :doc:`../traceability`.
