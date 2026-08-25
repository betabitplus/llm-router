@specification @hermetic @vcr @cap_video @cap_structured
Feature: Structured video understanding
  Local video input should produce structured observations grounded in visible action.

  Rule: The example clip produces grounded action and location evidence

    Scenario: QwenChat describes the example rooftop video
      Given the QwenChat video route
      When the route analyzes the example video:
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
