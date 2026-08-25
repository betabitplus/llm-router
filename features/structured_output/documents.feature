@specification @hermetic @vcr @cap_file @cap_structured
Feature: Structured document extraction
  Attached documents should produce structured facts grounded in their source text.

  Rule: A PDF digest stays tied to the attached paper

    Scenario: QwenChat extracts a grounded digest from the example PDF
      Given the QwenChat document route
      When the route analyzes the example PDF:
        """
        You are given a PDF file attachment.
        
        Extract content from the PDF (focus on the paper itself, not file metadata).
        Return JSON with:
        - metadata.title: exact paper title from page 1, as a single line
        - metadata.title_words: exactly 3 distinct words taken from the title, preserving case
        - abstract_one_sentence: one sentence summarizing the Abstract (<= 25 words)
        - contributions: exactly 3 short bullet points (<= 12 words each)
        - evidence: exactly 2 verbatim snippets copied from page 1 (8+ chars). Choose snippets that are not broken by hyphenation across lines.
          - source must be one of: title, abstract, introduction
        - key_entities: exactly 4 complete proper nouns or model names copied verbatim from the PDF (preserve case). Do not infer abbreviations, expand names, or use entities that are not literally printed in the document. Prefer author, institution, or model names you can see directly.
        
        Return ONLY valid JSON. No markdown.
        """
      Then the digest is grounded in the PDF text
