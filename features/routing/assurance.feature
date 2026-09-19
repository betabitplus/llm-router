@hermetic
Feature: Routing reliability assurance
  Upper-level routing assurance proves interactions and intended outcomes that are not owned by one Requirement in isolation.

  Rule: Route fallback remains useful as one capability

    Scenario: A degraded fallback chain recovers within the attempt budget
      Given a router has four eligible routes with an attempt budget of three
      And the first two eligible routes fail
      When a bounded recovery request is made
      Then the third route satisfies the request
      And no route beyond the attempt budget is contacted

  Rule: Rate-limit awareness composes with fallback

    Scenario: A blocked preferred route can still fall through a failing route to success
      Given a three-route router whose preferred route can be rate-limited
      And the next eligible route fails at the provider boundary
      When a cross-capability recovery request is made
      Then the blocked route is skipped without a provider interaction
      And routing falls through to the later eligible route

  Rule: The routing goal preserves predictable progress

    Scenario: Recovery remains the preferred path on the next request
      Given a three-route router under temporary availability degradation
      And an eligible fallback route fails before a later route succeeds
      When recovery and a follow-up request are made
      Then the degraded request still succeeds through an eligible route
      And the follow-up request starts from the recovered successful route
