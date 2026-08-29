@hermetic
Feature: Provider recovery
  Temporary provider failures and invalid structured responses can be recovered when policy allows it.

  Rule: Retryable failures are retried without changing routes

    @REQ_PROVIDER_RETRY[revision==1]
    Scenario: A temporary provider failure succeeds on retry
      Given a provider temporarily fails
      And the failure is retryable
      When the same provider succeeds on a later attempt
      Then the request succeeds without route fallback

    @REQ_PROVIDER_RETRY[revision==1]
    Scenario: A permanent provider failure is not retried
      Given a provider rejects a request permanently
      When the request is executed
      Then the provider is not retried

  Rule: Invalid structured output can be repaired

    @REQ_STRUCTURED_OUTPUT_REPAIR[revision==1]
    Scenario: Invalid structured output is repaired
      Given a provider first returns output that does not match the requested schema
      When a later repair attempt returns valid output
      Then the validated structured result is returned

    @REQ_STRUCTURED_OUTPUT_REPAIR[revision==1]
    Scenario: Structured output repair has a finite limit
      Given every repair attempt returns invalid output
      When the repair limit is reached
      Then the request fails with a public provider error
