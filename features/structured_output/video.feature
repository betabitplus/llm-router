@hermetic @vcr @REQ_VIDEO_INPUT[revision==1]
Feature: Structured video understanding
  Video input should produce structured observations grounded in visible action.

  Rule: A local clip produces grounded action and location evidence

    Scenario Outline: A provider route describes the example rooftop video
      Given the "<route>" local video route
      When the route analyzes the example rooftop video:
        """
        You are given a short video clip.
        
        Return JSON with exactly three keys:
        - action: the main action as a short lowercase verb or gerund
        - location: a short phrase describing where the action happens
        
        - evidence: exactly 2 short strings describing visible motion or scene cues
        
        If the clip shows a person jumping or leaping, use a value containing "jump" or "leap" for action.
        If it happens on a rooftop, skyscraper, or tall building, mention that in location.
        In evidence, mention motion or jump-related details.
        
        Return ONLY valid JSON. No markdown.
        """
      Then the observation is grounded in a rooftop jump

      Examples:
        | route         |
        | QwenChat      |
        | AI Studio     |
        | Gemini WebAPI |
        | Google GenAI  |

  Rule: A remote video URL can be analyzed without changing the public result contract

    Scenario Outline: A provider route describes the example remote video
      Given the "<route>" remote video route
      When the route analyzes the example remote video
      Then the observation is grounded in the indoor activity

      Examples:
        | route         |
        | AI Studio     |
        | Gemini WebAPI |
        | Google GenAI  |
