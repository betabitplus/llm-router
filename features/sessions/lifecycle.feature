@hermetic
Feature: Session lifecycle
  Sessions preserve conversation state and can be safely reset, persisted, and branched.

  Rule: Conversation history remains usable

    @REQ_SESSION_LIFECYCLE[revision==1]
    Scenario: Remembered turns are included in later messages
      Given a session contains previous conversation turns
      When a new message is built with history
      Then the previous turns appear before the new message

    @REQ_SESSION_LIFECYCLE[revision==1]
    Scenario: History can be ignored for one request
      Given a session contains previous conversation turns
      When a new message is built without history
      Then only the current message and system instruction are used

  Rule: Session state can be copied and persisted

    @REQ_SESSION_LIFECYCLE[revision==1]
    Scenario: A fork starts with the same history and then changes independently
      Given a session contains conversation history
      When the session is forked and the fork receives another turn
      Then the original session remains unchanged

    @REQ_SESSION_PERSISTENCE[revision==1]
    Scenario: Saving and loading preserves the session
      Given a session contains conversation history
      When it is saved and loaded
      Then its conversation state is preserved

    @REQ_SESSION_PERSISTENCE[revision==1]
    Scenario: Saving and loading preserves an embedded file
      Given a session contains an embedded file
      When it is saved and loaded
      Then the embedded file is preserved

    @REQ_SESSION_PERSISTENCE[revision==1]
    Scenario: Saving and loading preserves an embedded image
      Given a session contains an embedded image
      When it is saved and loaded
      Then the embedded image is preserved

    @REQ_SESSION_PERSISTENCE[revision==1]
    Scenario: Saving and loading preserves an embedded local video
      Given a session contains an embedded local video
      When it is saved and loaded
      Then the embedded local video is preserved

    @REQ_SESSION_PERSISTENCE[revision==1]
    Scenario: Saving and loading preserves a remote video descriptor
      Given a session contains a remote video descriptor
      When it is saved and loaded
      Then the remote video descriptor is preserved

    @REQ_SESSION_LIFECYCLE[revision==1]
    Scenario: Clearing a session removes history but keeps it reusable
      Given a session contains conversation history
      When the session is cleared
      Then its history is empty
      And new turns can still be added

  Rule: Independent sessions remain isolated during concurrent execution

    @REQ_SESSION_LIFECYCLE[revision==1]
    Scenario: Concurrent requests keep their session state separate
      Given two independent sessions execute concurrently
      When both requests complete
      Then each session contains only its own conversation
      And each request keeps its own routing result
