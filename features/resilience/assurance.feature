@hermetic
Feature: Resilient execution assurance
  Provider retry and structured-output recovery must compose without allowing combined recovery work to become unbounded.

  Rule: Provider retry composes with structured-output repair

    Scenario: A transient provider failure during repair is retried before recovery succeeds
      Given structured recovery has started from an invalid provider response
      When the repair turn transiently fails and then returns valid output
      Then the structured request succeeds after one repair retry

  Rule: Combined recovery budgets bound total provider work

    Scenario: Combined retry and structured budgets stop before a fifth provider interaction
      Given provider retry and structured recovery each have a two-attempt budget
      When each structured attempt consumes one transient retry and remains invalid
      Then the request fails after exactly four provider interactions
      And the fifth provider interaction is never made
