@specification @hermetic @vcr @cap_tools @cap_structured
Feature: Multi-round tool execution
  Tool-driven workflows should preserve their intermediate steps in the final result.

  Rule: Required tool use can complete a multi-step calculation

    Scenario: QwenChat completes a two-step calculation with tools
      Given the QwenChat multi-round tool route
      When the route executes the calculation workflow:
        """
        You have tools add(a, b) and multiply(a, b), each returning {result}.
        Step 1: use add with a=40 and b=2.
        Step 2: multiply the step-1 result by 2.
        Return JSON with:
        - steps: a list of tool call summaries with `tool_name` and `result`
        - final_result
        
        Return ONLY valid JSON. No markdown.
        """
      Then the structured workflow reports add and multiply with final result 84
