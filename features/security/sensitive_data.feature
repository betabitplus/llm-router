@hermetic @REQ_SENSITIVE_DATA_PROTECTION[revision==1]
Feature: Sensitive data protection
  Diagnostic output and recorded provider traffic must not expose secrets or user content.

  Rule: Sensitive values are removed from persisted diagnostics

    @TREQ_VCR_AUTH_REDACTION[revision==1]
    Scenario: Provider authentication is removed from VCR recordings
      Given a provider request contains authentication data
      When the interaction is recorded
      Then authentication secrets are absent from the recording

    @TREQ_RUNTIME_LOG_SAFETY[revision==1]
    Scenario: Runtime logs do not contain request or credential contents
      Given a request contains a secret prompt, credentials, and tool arguments
      When the request is processed
      Then those values do not appear in runtime logs
