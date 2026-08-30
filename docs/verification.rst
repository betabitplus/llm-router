Verification
============

This page answers two questions quickly: **is every requested verification layer
covered?** and **where do I inspect the concrete execution?** JUnit remains the
authoritative execution input imported into Sphinx-Needs; the views below only
present that evidence differently.

Release outcome
---------------

.. grid:: 2 2 4 4
   :gutter: 2

   .. grid-item-card:: Executed
      :class-card: portal-card

      :need_count:`type == "testcase"` tests

   .. grid-item-card:: Passed
      :class-card: portal-card

      :need_count:`type == "testcase" and result == "passed"` passed

   .. grid-item-card:: Failed / errored
      :class-card: portal-card

      :need_count:`type == "testcase" and (result == "failed" or result == "error")` failed or errored

   .. grid-item-card:: Skipped
      :class-card: portal-card

      :need_count:`type == "testcase" and result == "skipped"` skipped

Verification matrix
-------------------

The matrix keeps individual testcase IDs out of the overview. Rows are product
requirements and engineering constraints; columns are verification layers.
``x/x`` means all executions in that layer passed. ``missing`` means the object
requests that verification kind but no execution was found. A dash means that
layer is not requested.

.. raw:: html

   <iframe
     class="verification-matrix-frame"
     src="verification-matrix.html"
     title="Requirement verification matrix"
   ></iframe>

Inspect concrete evidence
-------------------------

.. grid:: 1 1 3 3
   :gutter: 3

   .. grid-item-card:: BDD stories
      :link: test-results/bdd/index.html
      :link-type: url
      :class-card: portal-card

      Read Feature → Rule → Scenario → Given/When/Then. Evidence is attached to
      the exact step that produced it.

   .. grid-item-card:: By requirement
      :link: test-results/requirements/index.html
      :link-type: url
      :class-card: portal-card

      Expand a requirement, then choose BDD, unit, integration, or property.
      Each entry remains the real execution result with human-readable title,
      status, timing, parameters, and any runtime attachments.

   .. grid-item-card:: All tests by layer
      :link: test-results/all/index.html
      :link-type: url
      :class-card: portal-card

      Browse all 117 executions when you need engineering-level inventory rather
      than product navigation.

How traceability fits
---------------------

A requirement page remains the authoritative place for ``derives from``,
``implemented by``, and ``verified by`` relationships. The matrix deliberately
aggregates testcase IDs because showing dozens of execution nodes is useful for
provenance but poor for reading the product model.

For exact implementation markers use :doc:`traceability`. For behavioral review
use :doc:`specifications`. The raw JUnit-imported hierarchy is available at
:doc:`local-pytest-evidence` for diagnostics and provenance.
