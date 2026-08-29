Verification evidence
=====================

This page is the human-facing view of the authoritative pytest evidence imported
from JUnit into the Sphinx-Needs graph. Each testcase ID links to its imported
testcase record, including the observed result and the requirement revisions it
verifies.

BDD scenarios
-------------

BDD evidence keeps the Gherkin source and scenario name next to the pytest
result, so the executable specification and its requirement link can be reviewed
together.

.. needtable::
   :columns: id;title;result;gherkin_feature;gherkin_scenario;verifies
   :filter: type == "testcase" and verification_kind == "bdd"

Unit tests
----------

.. needtable::
   :columns: id;title;result;classname;verifies
   :filter: type == "testcase" and verification_kind == "unit"

Integration tests
-----------------

.. needtable::
   :columns: id;title;result;classname;verifies
   :filter: type == "testcase" and verification_kind == "integration"

Property tests
--------------

.. needtable::
   :columns: id;title;result;classname;verifies
   :filter: type == "testcase" and verification_kind == "property"

End-to-end tests
----------------

The table is intentionally empty when no requirement asks for end-to-end
evidence in the current graph.

.. needtable::
   :columns: id;title;result;classname;verifies
   :filter: type == "testcase" and verification_kind == "e2e"

Raw imported evidence
---------------------

The release documentation also contains the raw JUnit-imported testcase page.
Its ``testsuite -> testfile -> testcase`` links preserve the structure of the
JUnit report; they are graph-navigation links rather than separate reports. Use
the categorized tables above for normal review, and open a testcase ID when the
full imported record is needed.
