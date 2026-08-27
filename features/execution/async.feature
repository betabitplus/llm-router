@hermetic @vcr
Feature: Async public execution
  Async calls should preserve the same useful result contracts as synchronous calls.

  Rule: The public async entry point returns the requested result

    Scenario: QwenChat returns a short text reply asynchronously
      Given the QwenChat async route
      When the async route receives:
        """
        Reply with only: pong
        """
      Then the normalized reply is "pong"

    Scenario: Gemini WebAPI returns a short text reply asynchronously
      Given the Gemini WebAPI async route
      When the async route receives:
        """
        Reply with only: pong
        """
      Then the normalized reply is "pong"

    Scenario: An OpenAI-compatible route extracts a legal case asynchronously
      Given the OpenAI-compatible async route
      When the async route extracts a legal case from:
        """
        In the High Court of Techville. Case No. 2025-CV-001.
        
        Between:
        Global AI Corp (a Delaware corporation), Plaintiff
        v.
        John Doe (an individual) and Hackers United Ltd., Defendants.
        
        Summary:
        Global AI Corp alleges that John Doe, a former employee, stole proprietary
        algorithms and shared them with Hackers United Ltd. The plaintiff claims
        breach of contract and trade secret misappropriation.
        They are seeking $10 million in damages and a permanent injunction
        preventing further use of the algorithms.
        """
      Then the structured case preserves its parties and legal issues

    Scenario: AI Studio returns structured movie data asynchronously
      Given the AI Studio async route
      When the async route requests the example movie record
      Then the structured movie record is grounded in Inception

    Scenario: Google GenAI analyzes an image asynchronously
      Given the Google GenAI async image route
      When the async route analyzes the example traffic image
      Then the async image result is a grounded traffic scene
