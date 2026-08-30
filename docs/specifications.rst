Executable specifications
=========================

This is the narrative-first BDD view. The embedded report is generated from the
same pytest run used for JUnit traceability, but it is organized as executable
behavior instead of Python packages:

``Feature → Rule → Scenario → Given / When / Then → evidence``.

Attachments are shown inside the step that produced them. For example, image
scenarios place the input image under ``When`` and the structured result JSON
under ``Then``.

.. button-link:: test-results/bdd/index.html
   :color: primary
   :shadow:

   Open BDD stories full screen

.. raw:: html

   <iframe
     class="test-portal-frame"
     src="test-results/bdd/index.html"
     title="llm-router executable specifications"
   ></iframe>

Gherkin source catalogue
------------------------

The report above is the primary reading experience. The source specifications
below are included directly from ``features/`` for exact review and provenance.
They are not a second specification model.

Structured image understanding
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../features/structured_output/images.feature
   :language: gherkin
   :linenos:

Structured document extraction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../features/structured_output/documents.feature
   :language: gherkin
   :linenos:

Structured video understanding
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../features/structured_output/video.feature
   :language: gherkin
   :linenos:

Structured text output
~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../features/structured_output/text.feature
   :language: gherkin
   :linenos:

Route fallback
~~~~~~~~~~~~~~

.. literalinclude:: ../features/routing/fallback.feature
   :language: gherkin
   :linenos:

Route availability
~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../features/routing/rate_limits.feature
   :language: gherkin
   :linenos:

Provider recovery
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../features/resilience/recovery.feature
   :language: gherkin
   :linenos:

Configuration overrides
~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../features/configuration/overrides.feature
   :language: gherkin
   :linenos:

Async public execution
~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../features/execution/async.feature
   :language: gherkin
   :linenos:

Public response contract
~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../features/responses/public_contract.feature
   :language: gherkin
   :linenos:

Sensitive data protection
~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../features/security/sensitive_data.feature
   :language: gherkin
   :linenos:

Session lifecycle
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../features/sessions/lifecycle.feature
   :language: gherkin
   :linenos:

Tool execution
~~~~~~~~~~~~~~

.. literalinclude:: ../features/tools/runtime.feature
   :language: gherkin
   :linenos:

Explicit tool choice
~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../features/tools/tool_choice.feature
   :language: gherkin
   :linenos:

Multi-round tool execution
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../features/tools/multi_round.feature
   :language: gherkin
   :linenos:
