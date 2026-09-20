@hermetic
Feature: Sensitive data protection
  Public diagnostics and retained replay evidence must stay useful without persisting protected caller or provider-controlled values.

  Rule: Public success diagnostics remain bounded

    @REQ_SENSITIVE_DATA_PROTECTION[revision==1]
    Scenario: Successful request diagnostics exclude protected prompt and credential
      Given a successful request contains a protected prompt and credential
      When the successful request crosses the public router boundary
      Then successful request diagnostics contain no protected caller values

  Rule: Protected values do not cross the public diagnostic boundary

    @TREQ_RUNTIME_LOG_SAFETY[revision==2]
    Scenario: Provider failure diagnostics exclude provider-controlled protected text
      Given a provider error contains protected diagnostic text and a protected credential
      When the provider failure crosses the public router boundary
      Then provider failure diagnostics contain only safe failure metadata

    @TREQ_RUNTIME_LOG_SAFETY[revision==2]
    Scenario: Tool failure diagnostics exclude caller and tool-cause content
      Given a request contains protected prompt, credential, tool arguments, and tool-cause text
      When the protected local tool fails
      Then tool failure diagnostics contain only safe tool metadata

    @TREQ_RUNTIME_LOG_SAFETY[revision==2]
    Scenario: Schema failure diagnostics exclude invalid values and caller schema identity
      Given structured output validation contains protected caller-controlled values
      When structured validation exhausts its public attempt budget
      Then schema failure diagnostics contain only safe validation metadata
