@hermetic
Feature: Session continuity assurance
  Upper-level session assurance proves that lifecycle isolation and persistence compose into safe conversational continuity.

  Rule: Branching and persistence compose without aliasing

    Scenario: A persisted fork keeps branch state without changing its source
      Given a session contains a remembered source turn
      When a fork is extended, persisted, and restored
      Then the source session remains unchanged
      And the restored branch contains the source and branch turns

  Rule: Restored sessions resume through the public router without cross-session contamination

    Scenario: A restored session continues independently from its sibling
      Given a persisted session and an independent sibling session
      When the restored session continues through the public router
      Then the provider receives the restored history before the new message
      And only the restored session remembers the provider response
