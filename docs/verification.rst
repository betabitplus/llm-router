Verification evidence
=====================

This page is the human-facing view of the authoritative pytest evidence imported
from the release JUnit report into the Sphinx-Needs graph. It does not create a
second test report: every row below is a view of the same imported testcase Need
that satisfies the requirements graph.

Release test outcome
--------------------

The suite summary comes directly from the imported JUnit run used to build the
release documentation.

.. needtable::
   :columns: title as "Suite";cases as "Cases";passed as "Passed";failed as "Failed";errors as "Errors";skipped as "Skipped"
   :filter: type == "testsuite"

The current evidence inventory contains:

* :need_count:`type == "testcase" and verification_kind == "bdd"` BDD testcase(s)
* :need_count:`type == "testcase" and verification_kind == "unit"` unit testcase(s)
* :need_count:`type == "testcase" and verification_kind == "integration"` integration testcase(s)
* :need_count:`type == "testcase" and verification_kind == "property"` property testcase(s)
* :need_count:`type == "testcase" and verification_kind == "e2e"` end-to-end testcase(s)

Requirement-to-evidence chain
-----------------------------

This is the complete requirement-level chain. ``Needs Artifacts`` says which
implementation or verification kinds are required. ``Implemented By`` links to
the exact implementation marker and source location. ``Verified By`` links to
the concrete executed testcase records. The categorized testcase tables below
show the result, duration, source, and verification kind for those testcase IDs.

.. needtable::
   :columns: id;title;needs_artifacts as "Required evidence";implements_back as "Implemented by";verifies_back as "Verified by"
   :filter: type in ["req", "treq"]

BDD scenarios
-------------

BDD evidence connects an executable Gherkin scenario to its pytest execution and
requirement revision. ``Feature source`` and ``Test source`` link to the exact
release tag in GitHub; ``Result`` and ``Duration`` come from the release JUnit
execution.

.. needtable::
   :columns: id;result;time as "Duration (s)";gherkin_scenario as "Scenario";gherkin_feature as "Feature source";classname as "Test source";verifies as "Requirement"
   :filter: type == "testcase" and verification_kind == "bdd"
   :style_row: tr_[[copy('result')]]

Unit tests
----------

.. needtable::
   :columns: id;title;result;time as "Duration (s)";classname as "Test source";verifies as "Requirement"
   :filter: type == "testcase" and verification_kind == "unit"
   :style_row: tr_[[copy('result')]]

Integration tests
-----------------

.. needtable::
   :columns: id;title;result;time as "Duration (s)";classname as "Test source";verifies as "Requirement"
   :filter: type == "testcase" and verification_kind == "integration"
   :style_row: tr_[[copy('result')]]

Property tests
--------------

.. needtable::
   :columns: id;title;result;time as "Duration (s)";classname as "Test source";verifies as "Requirement"
   :filter: type == "testcase" and verification_kind == "property"
   :style_row: tr_[[copy('result')]]

End-to-end tests
----------------

The table is intentionally empty when no requirement asks for end-to-end
evidence in the current graph. An empty table therefore means ``e2e`` is not a
required verification kind for this release, not that a requested test was lost.

.. needtable::
   :columns: id;title;result;time as "Duration (s)";classname as "Test source";verifies as "Requirement"
   :filter: type == "testcase" and verification_kind == "e2e"
   :style_row: tr_[[copy('result')]]

Visual and media evidence
-------------------------

``llm-router`` is an API library, so its pytest evidence does not manufacture a
screenshot for every testcase. A screenshot of a green test runner would add no
behavioral proof beyond the imported JUnit result. For image, document, and video
BDD scenarios the feature and test-source links above identify the executable
scenario and its assertions. The :doc:`live multimodal example
<auto_examples/multimodal_inputs>` renders representative media inputs and
outputs for human inspection, but examples remain demonstrations rather than a
replacement for testcase evidence.

Raw imported evidence
---------------------

The release documentation also contains the raw JUnit-imported testcase page.
Its ``testsuite -> testfile -> testcase`` links preserve the structure of the
JUnit report. The raw testcase cards intentionally expose lower-level imported
metadata and are useful for provenance/debugging; use the categorized tables
above for normal review because all relevant result/source/requirement fields are
visible without expanding a collapsed card.
