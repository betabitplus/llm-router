@hermetic
Feature: Provider portability assurance
  Provider-family changes should preserve the public success, asynchronous, and failure contracts.

  Rule: Public success and error contracts compose

    Scenario: One provider route preserves the public success and error boundary
      Given an OpenAI-compatible route returns one normalized success and then rejects
      When both requests cross the public router boundary
      Then the first request preserves the normalized success contract
      And the later rejection preserves the public provider-error contract

  Rule: Provider family and execution mode can change together

    Scenario: Sync OpenAI-compatible and async Google preserve the same success meaning
      Given equivalent OpenAI-compatible and Google success responses
      When the OpenAI-compatible request runs synchronously and Google runs asynchronously
      Then both requests preserve the same public success meaning

  Rule: Provider swapping preserves the whole caller-facing outcome

    Scenario: A provider swap preserves success semantics and a later failure boundary
      Given equivalent OpenAI-compatible and Google success responses followed by a Google rejection
      When the caller executes across both provider families and then receives the rejection
      Then the successful responses preserve the same public meaning
      And the later Google rejection remains a public provider error
