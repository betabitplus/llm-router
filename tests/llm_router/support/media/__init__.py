"""Media-oriented llm_router test support helpers.

Why:
    Keeps image, video, pdf, and media-provider scenario helpers grouped under
    one clear support area.

What belongs here:
    Shared media schemas, prompts, assertions, and runtime guards used by
    llm_router e2e capability scenarios.

What does not belong here:
    General test infrastructure, VCR support, or subprocess worker helpers.
"""
