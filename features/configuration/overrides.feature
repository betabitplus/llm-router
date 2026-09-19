@hermetic @REQ_REQUEST_OVERRIDE_PRECEDENCE[revision==1]
Feature: Configuration overrides
  Requests can override router and route defaults without changing unrelated settings.

  Rule: More specific settings take precedence

    Scenario: Request settings override router and route defaults
      Given a route and router define different generation settings
      When a request provides its own settings
      Then the request settings are used
      And unrelated defaults are preserved

    Scenario: An explicit null value removes an inherited optional setting
      Given structured output is enabled by a default
      When the request explicitly disables structured output
      Then the request is executed without structured output

    Scenario: An explicit empty collection removes inherited tools
      Given tools are enabled by a default
      When the request explicitly supplies no tools
      Then the request is executed without provider tools
