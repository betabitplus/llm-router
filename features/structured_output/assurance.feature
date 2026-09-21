@hermetic
Feature: Rich input and structured-output assurance
  Rich caller intent and caller schemas should remain provider-independent at the public router boundary.

  Rule: Rich content and schema compose

    Scenario: Rich image input and caller schema survive one provider boundary
      Given a rich image request with a caller schema
      When the request crosses an OpenAI-compatible provider boundary
      Then the provider receives both the image and caller schema
      And the public result is reconstructed from the requested schema

  Rule: Invalid schemas still fail before providers

    Scenario: Invalid schema cannot bypass validation through rich input
      Given a rich image request with an invalid caller schema
      When the invalid rich request is submitted
      Then schema normalization fails before provider execution

  Rule: Provider swaps preserve rich structured meaning

    Scenario: Two provider families preserve the same rich structured outcome
      Given equivalent OpenAI-compatible and Google rich structured responses
      When the same image-and-schema intent runs through both provider families
      Then both providers return the same public structured meaning
