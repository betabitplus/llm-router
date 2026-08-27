@hermetic
Feature: Sensitive data protection
  Diagnostic output and recorded provider traffic must not expose secrets or user content.

  Rule: Sensitive values are removed from persisted diagnostics

    Scenario: Provider authentication is removed from VCR recordings
      Given a provider request contains authentication data
      When the interaction is recorded
      Then authentication secrets are absent from the recording

    Scenario: Runtime logs do not contain request or credential contents
      Given a request contains a secret prompt, credentials, and tool arguments
      When the request is processed
      Then those values do not appear in runtime logs
