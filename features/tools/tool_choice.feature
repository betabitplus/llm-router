@specification @hermetic @vcr @cap_tools @cap_structured
Feature: Explicit tool choice
  A named tool choice should be honored before the final structured answer is returned.

  Rule: A forced named tool is the only tool used

    Scenario Outline: A provider route honors an explicit add tool choice
      Given the "<route>" tool-choice route
      When the route is forced to use add:
        """
        You have tools add(a, b) and multiply(a, b), each returning {result}.
        Use ONLY add with a=40 and b=2, then return JSON with:
        - tool_name
        - final_result
        - explanation
        
        Return ONLY valid JSON. No markdown.
        """
      Then the structured result and runtime trace show only add with result 42

      Examples:
        | route             |
        | QwenChat          |
        | OpenAI-compatible |
