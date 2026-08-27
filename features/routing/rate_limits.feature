@specification @hermetic @cap_routing
Feature: Route availability
  Temporarily unavailable routes should not prevent useful alternatives from running.

  Rule: Blocked routes follow the configured waiting policy

    Scenario: A blocked route is skipped when another route is available
      Given the preferred route is temporarily blocked
      And another route is available
      When a request is made
      Then the available route is used

    @vcr
    Scenario: The router fails immediately when every route is blocked and waiting is disabled
      Given every route is temporarily blocked
      And waiting for availability is disabled
      When a request is made
      Then the request fails without waiting

    @vcr
    Scenario: The router waits when every route is blocked and waiting is enabled
      Given every route is temporarily blocked
      And waiting for availability is enabled
      When a route becomes available
      Then the request continues on that route

  Rule: Automatic key selection uses available capacity before waiting

    @vcr @cap_async
    Scenario: Requests rotate across available keys before waiting for reuse
      Given a provider route uses automatic key selection with two keys
      When three asynchronous requests are made in sequence
      Then the first two requests use different keys
      And the third request waits for an available key
