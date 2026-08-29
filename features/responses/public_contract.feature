@hermetic
Feature: Public response contract
  Provider-specific implementations should expose the same stable public response model.

  Rule: Equivalent successful provider responses normalize to the same public shape

    @REQ_RESPONSE_NORMALIZATION[revision==1]
    Scenario: OpenAI-compatible and Google routes normalize equivalent replies consistently
      Given equivalent successful responses from OpenAI-compatible and Google routes
      When both responses cross the public router boundary
      Then their visible text and usage have the same normalized shape
      And provider-specific transport details do not leak into tool fields

  Rule: Public failure categories remain specific

    @REQ_CREDENTIAL_RESOLUTION[revision==1]
    Scenario: Missing credentials surface as a missing-key error
      Given a request has no configured API key
      When it reaches the public router boundary
      Then it fails with a missing-key error

    @REQ_INVALID_CONFIGURATION_ERRORS[revision==1]
    Scenario: Invalid model configuration surfaces as a configuration error
      Given a request uses an unknown model
      When it reaches the public router boundary
      Then it fails with a configuration error

    @REQ_PROVIDER_ERROR_BOUNDARY[revision==1]
    Scenario: A provider HTTP failure surfaces as a provider error
      Given a provider rejects a valid request
      When the failure reaches the public router boundary
      Then it fails with a provider error
