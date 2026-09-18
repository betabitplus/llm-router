@hermetic @REQ_RATE_LIMIT_ROUTING[revision==1]
Feature: Route availability
  Temporarily unavailable routes should not prevent useful alternatives from running.

  Rule: Blocked routes follow the configured waiting policy

    Scenario: A blocked route is skipped when another route is available
      Given the preferred route is temporarily blocked
      And another route is available
      When a request is made
      Then the available route is used

    Scenario: The router fails immediately when every route is blocked and waiting is disabled
      Given every route is temporarily blocked
      And waiting for availability is disabled
      When a request is made
      Then the request fails without waiting

    @TREQ_RATE_LIMIT_AVAILABILITY_SELECTION[revision==1]
    Scenario: The router waits when every route is blocked and waiting is enabled
      Given every route is temporarily blocked
      And waiting for availability is enabled
      When a route becomes available
      Then the request continues on that route

  Rule: Automatic key selection uses available capacity before waiting

    Scenario: Requests rotate across available keys before waiting for reuse
      Given a provider route uses automatic key selection with two keys
      When three asynchronous requests are made in sequence
      Then the first two requests use different keys
      And the third request waits for an available key

    @TREQ_RATE_LIMIT_AVAILABILITY_SELECTION[revision==1]
    Scenario: An available key is used instead of waiting for a blocked key
      Given an automatic-key route with one cooled-down key and one available key
      When a request is made while the next rotating key is still blocked
      Then the available key is used without waiting
