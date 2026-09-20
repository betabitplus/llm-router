@hermetic
Feature: Tool orchestration assurance
  Upper-level tool assurance proves that selection, execution, and bounded failure semantics compose across capability boundaries.

  Rule: Tool execution requirements compose across multiple rounds

    Scenario: A successful tool round followed by a failing tool stops before another provider turn
      Given a tool workflow succeeds once before a later local tool fails
      When the multi-round workflow is executed
      Then the first tool result reaches the next provider turn
      And the later tool failure is public and no extra provider turn is made

  Rule: Tool selection and execution compose across capabilities

    Scenario: A forced named tool result is returned before the final provider response
      Given a local route with add and multiply tools
      When add is explicitly selected and executed
      Then only add is executed
      And the add result reaches the final provider turn
