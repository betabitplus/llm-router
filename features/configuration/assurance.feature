@hermetic
Feature: Configuration predictability assurance
  Installed configuration, credentials, layered defaults, and validation should compose into one predictable public runtime view.

  Rule: Effective configuration sources compose

    Scenario: Installed credentials and request overrides compose predictably
      Given a replacement configuration and credential are ready
      When a request combines router defaults route defaults and a call override
      Then the provider request uses the replacement credential and call override
      And the unrelated route default remains effective

  Rule: Validation remains effective after configuration replacement

    Scenario: Invalid requests remain pre-provider failures after installation
      Given a valid replacement configuration is active
      When an unknown model is requested after installation
      Then the request fails with a public configuration error before provider execution
      And the replacement configuration remains active
