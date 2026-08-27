@hermetic
Feature: Route fallback
  A router can try alternative routes when the preferred route cannot complete the request.

  Rule: Routes are attempted according to routing policy

    @REQ_SYNC_ROUTE_FALLBACK[revision==1]
    Scenario: A failed route falls back to the next route
      Given the router has two available routes
      And the first route fails
      When a request is made
      Then the second route is used
      And the routing trace contains both attempts

    Scenario: A timed-out route falls back without waiting for it indefinitely
      Given the first route exceeds its attempt timeout
      And another route is available
      When a request is made
      Then the request continues with the next route

    Scenario: A terminal route timeout is exposed when no fallback remains
      Given the only route exceeds its attempt timeout
      When the timed-out request is executed
      Then the request fails with a timeout error

    Scenario: The router does not exceed the configured number of route attempts
      Given more routes are available than the allowed attempt count
      When all attempted routes fail
      Then no additional routes are attempted

  Rule: Successful fallback advances the next starting route

    @vcr
    Scenario: The next request starts from the route that previously succeeded
      Given a public router whose preferred route fails
      When two requests are made through the same router
      Then the first request succeeds through fallback
      And the second request starts from the previously successful route
