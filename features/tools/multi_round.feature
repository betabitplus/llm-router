@hermetic @vcr @REQ_MULTI_ROUND_TOOL_EXECUTION[revision==1]
Feature: Multi-round tool execution
  Tool-driven workflows should preserve their intermediate steps in the final result.

  Rule: Required tool use can complete a multi-step calculation

    Scenario Outline: A provider route completes a two-step calculation with tools
      Given the "<route>" multi-round tool route
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

      Examples:
        | route         |
        | QwenChat      |
        | AI Studio     |
        | Gemini WebAPI |

  Rule: Tools configured on a route profile are available to requests

    Scenario: Google GenAI uses a profile-level tool in a structured workflow
      Given a Google GenAI route with a profile-level multiply tool
      When the route is required to calculate 17 times 19
      Then the structured result and runtime trace report multiply with result 323
