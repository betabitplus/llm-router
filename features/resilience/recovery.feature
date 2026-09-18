@hermetic
Feature: Provider recovery
  Temporary provider failures and invalid structured responses can be recovered when policy allows it.

  Rule: Retryable failures are retried without changing routes

    @REQ_PROVIDER_RETRY[revision==2]
    Scenario: A temporary provider failure succeeds on retry
      Given a provider temporarily fails
      And the failure is retryable
      When the same provider succeeds on a later attempt
      Then the request succeeds without route fallback

    @REQ_PROVIDER_RETRY[revision==2]
    Scenario: A permanent provider failure is not retried
      Given a provider rejects a request permanently
      When the request is executed
      Then the provider is not retried

    @REQ_PROVIDER_RETRY[revision==2]
    Scenario: An asynchronous temporary provider failure succeeds on retry
      Given a provider temporarily fails during asynchronous execution
      When the same provider succeeds on a later asynchronous attempt
      Then the asynchronous request succeeds without route fallback

    @REQ_PROVIDER_RETRY[revision==2]
    Scenario: An asynchronous permanent provider failure is not retried
      Given a provider rejects an asynchronous request permanently
      When the asynchronous request is executed
      Then the provider is not retried asynchronously

    @REQ_PROVIDER_RETRY[revision==2] @TREQ_PROVIDER_RETRY_BOUNDS[revision==1]
    Scenario: Synchronous provider retry stops at the configured attempt limit
      Given a provider keeps failing with retryable errors
      When synchronous retry exhausts a two-attempt budget
      Then exactly two synchronous provider attempts are made

    @REQ_PROVIDER_RETRY[revision==2] @TREQ_PROVIDER_RETRY_BOUNDS[revision==1]
    Scenario: Asynchronous provider retry stops at the configured attempt limit
      Given a provider keeps failing asynchronously with retryable errors
      When asynchronous retry exhausts a two-attempt budget
      Then exactly two asynchronous provider attempts are made

  Rule: Invalid structured output can be repaired

    @REQ_STRUCTURED_OUTPUT_REPAIR[revision==2]
    Scenario: Invalid structured output is repaired
      Given a provider first returns output that does not match the requested schema
      When a later repair attempt returns valid output
      Then the validated structured result is returned

    @REQ_STRUCTURED_OUTPUT_REPAIR[revision==2] @TREQ_STRUCTURED_OUTPUT_ATTEMPT_BOUNDS[revision==1]
    Scenario: Structured output stops at a one-attempt budget
      Given every structured response is invalid
      When structured output runs with a one-attempt budget
      Then exactly one structured provider response is evaluated

    @REQ_STRUCTURED_OUTPUT_REPAIR[revision==2] @TREQ_STRUCTURED_OUTPUT_ATTEMPT_BOUNDS[revision==1]
    Scenario: Structured output stops at a two-attempt budget
      Given every structured response is invalid
      When structured output runs with a two-attempt budget
      Then exactly two structured provider responses are evaluated
