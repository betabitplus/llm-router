Test results
============

Concrete executions are presented in several views because one hierarchy does not
fit every review task. All views below are generated from the same pytest run;
JUnit remains the authoritative verification input for Sphinx-Needs.

Current verification inventory
------------------------------

.. grid:: 1 2 4 4
   :gutter: 2

   .. grid-item-card:: BDD
      :class-card: portal-card

      :need_count:`type == "testcase" and verification_kind == "bdd"` executable scenarios

   .. grid-item-card:: Unit
      :class-card: portal-card

      :need_count:`type == "testcase" and verification_kind == "unit"` unit tests

   .. grid-item-card:: Integration
      :class-card: portal-card

      :need_count:`type == "testcase" and verification_kind == "integration"` integration tests

   .. grid-item-card:: Property
      :class-card: portal-card

      :need_count:`type == "testcase" and verification_kind == "property"` property tests

Choose a perspective
--------------------

.. grid:: 1 1 3 3
   :gutter: 3

   .. grid-item-card:: BDD stories
      :link: test-results/bdd/index.html
      :link-type: url
      :class-card: portal-card

      Read Feature → Rule → Scenario executions as a narrative. Given/When/Then
      steps contain the images, JSON, PDFs, videos, doc strings, and other
      evidence produced during that exact step.

   .. grid-item-card:: Verification by requirement
      :link: test-results/requirements/index.html
      :link-type: url
      :class-card: portal-card

      Start from a requirement, then inspect its BDD, unit, integration, or
      property executions. Human-readable test titles, parameters, status, timing,
      and available runtime attachments stay attached to the real execution result.

   .. grid-item-card:: All tests by layer
      :link: test-results/all/index.html
      :link-type: url
      :class-card: portal-card

      Browse the complete execution inventory grouped by verification layer.
      Useful for engineering review rather than product navigation.

Requirement-centric test evidence
---------------------------------

The embedded view starts from the requirement instead of from Python package
names. Open it full-screen when you want more horizontal space.

.. button-link:: test-results/requirements/index.html
   :color: primary
   :shadow:

   Open verification by requirement full screen

.. raw:: html

   <iframe
     class="test-portal-frame"
     src="test-results/requirements/index.html"
     title="llm-router verification by requirement"
   ></iframe>

For the behavioral narrative use :doc:`specifications`. For the authoritative
requirement-to-test links and raw JUnit provenance use :doc:`verification`.
