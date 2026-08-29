@hermetic @vcr @REQ_IMAGE_INPUT[revision==1]
Feature: Structured image understanding
  The same image contract should remain valid across supported provider routes.

  Rule: A traffic image produces grounded structured evidence

    Scenario Outline: A provider route describes the example traffic image
      Given the "<route>" image route
      When the route analyzes the example traffic image:
        """
        Describe the attached image and return JSON.
        
        Return exactly these keys:
        - primary_subject: a short phrase naming the main thing shown
        - setting: a short phrase describing the setting
        - visible_objects: at least 3 short object names
        - evidence: at least 2 short phrases grounding the answer in the image
        
        If the scene is a road, highway, or traffic setting, mention that clearly.
        Return ONLY valid JSON. No markdown.
        """
      Then the result is a grounded traffic scene

      Examples:
        | route             |
        | QwenChat          |
        | OpenAI-compatible |
        | AI Studio         |
        | Gemini WebAPI     |
