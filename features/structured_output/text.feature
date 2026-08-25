@specification @hermetic @vcr @cap_structured
Feature: Structured text output
  Plain text requests should be convertible into validated structured records.

  Rule: Requested structure and fixed facts are preserved

    Scenario: QwenChat creates a deterministic incident report
      Given the QwenChat structured text route
      When the route receives the incident request:
        """
        Create an incident report for a simulated outage.
        
        Constraints:
        - Use incident_id: INC-1042
        - Severity: SEV2
        - Environment for services: prod
        - affected_services: exactly 2 items
        - timeline: exactly 4 events
        - remediation_items: exactly 3 items
        - Keep all strings short and professional.
        """
      Then the incident report preserves the required identifiers and list sizes
