@specification @hermetic @cap_tools @cap_resilience
Feature: Tool execution
  Tool workflows should either complete predictably or fail through the public API.

  Rule: Tool execution has explicit failure and termination behavior

    Scenario: A local tool failure becomes a public tool error
      Given a model requests a registered tool
      And the tool fails
      When the tool call is executed
      Then the request fails with a tool execution error
      And no further provider turn is made

    Scenario: Tool execution stops at the configured round limit
      Given the model continues requesting tools
      When the maximum tool round count is reached
      Then no additional tool round is executed
      And the outstanding tool call remains visible in the response
