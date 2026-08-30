Requirements traceability
=========================

Requirements are the engineering source of truth. Verification and implementation
evidence are linked into the same Sphinx-Needs graph. Product requirements and
engineering constraints carry an explicit ``draft`` / ``accepted`` / ``deprecated``
lifecycle state; semantic changes advance ``revision`` so existing evidence must
be reviewed against the new contract.

Requirement hierarchy
---------------------

.. needtable::
   :columns: id;title;type;status;derives;derives_back
   :filter: type in ["goal", "feature", "req", "treq"]

Implementation evidence
-----------------------

Implementation markers live next to the code they justify::

   # @impl Short implementation title, IMPL_EXAMPLE, [REQ_EXAMPLE[revision==1]]

The marker creates an ``IMPL_*`` need with a source link and an ``implements``
edge to the referenced requirement revision. Requirements that request ``impl``
evidence must have at least one such incoming edge; a requirement revision bump
invalidates stale implementation links until they are reviewed and repinned.

.. src-trace::
   :project: python

Verification evidence
---------------------

Pytest evidence links to an exact requirement revision and declares its evidence
kind. A requested verification kind is satisfied only by a testcase whose result
is ``passed``; skipped and expected-failure results remain visible evidence but do
not satisfy the requirement obligation. Revision bumps invalidate stale
``verifies`` links until the verification has been reviewed and repinned.

For normal human review, :doc:`verification` groups the same imported testcase
Needs by BDD, unit, integration, property, and end-to-end verification kind.

Evidence matrices
-----------------

Requirement evidence coverage:

.. needtable::
   :columns: id;title;status;revision;required_evidence;implements_back;verifies_back
   :filter: type in ["req", "treq"]

Non-passing verification evidence (empty on a healthy build):

.. needtable::
   :columns: id;title;result;verification_kind;verifies
   :filter: type == "testcase" and result != "passed"

Execution evidence and agent views
----------------------------------

Required CI publishes one ``python-test-evidence-<sha>`` artifact containing the
pytest JUnit report, the context-enabled ``.coverage`` database,
``coverage.json`` with per-test contexts, and raw ``allure-results``. JUnit is
the authoritative verification input imported into Sphinx-Needs. Coverage
contexts and Allure remain auxiliary execution evidence. Allure is rendered as
the human-facing :doc:`test portal <tests>` so images, JSON, logs, PDFs, and
videos can be inspected directly, but it does not define trace links or satisfy
requirement obligations; JUnit and Sphinx-Needs remain authoritative.

The built documentation already exposes the authoritative graph as
``needs.json`` and provides derived agent-readable page Markdown plus
``llms.txt`` and ``llms-full.txt``. A separate ``ai_docs_index.json`` is
therefore intentionally not generated because it would duplicate those views.

Graph inventory
---------------

.. needtable::
   :columns: id;title;type;required_evidence
   :filter: type in ["goal", "feature", "req", "treq", "impl", "testcase"]
