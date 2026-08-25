Feature: QwenChat structured output
  Turn a plain-text request into a validated incident report while preserving
  the requested structured contract.

  Rule: Requested incident-report constraints are preserved
    Structured output must preserve the explicitly requested identifiers and
    collection sizes that make the result useful to downstream code.

    Scenario: Convert a plain-text request into an incident report
      A deterministic request makes the replayed evidence easy to inspect and
      the expected contract obvious to a human reader.

      When QwenChat is asked for a deterministic incident report
      Then a structured incident report is returned
      And the incident id is INC-1042
      And it contains 2 affected services
      And it contains 4 timeline events
      And it contains 3 remediation items
