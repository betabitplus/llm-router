(assurance-profile-developer-usability)=

# Assurance profile · Developer usability

**Scope:** {need}`GOAL_DEVELOPER_USABILITY` and its direct Feature branches.

**Policy:** {ref}`Upper-level assurance and validation <test-plan-upper-level-assurance>`

This profile declares only upper-level Targets that cannot be reduced to one Requirement. Child-support gates come from the authoritative Sphinx-Needs `derives` graph.

## Feature · FEAT_PUBLIC_API

**Requirement support:** ALL direct Requirements deriving from {need}`FEAT_PUBLIC_API`.

### Capability integration

**Target:** N/A — the Feature has one direct Requirement, so there is no cross-Requirement interaction to prove at this level.

### Capability validation

**Target:** N/A — the Feature claim is exactly the package-root resolution contract already owned by {need}`REQ_PUBLIC_API_SURFACE`; duplicating that proof at Feature level would add no distinct validation claim.

## Feature · FEAT_EXECUTABLE_EXAMPLES

**Requirement support:** ALL direct Requirements deriving from {need}`FEAT_EXECUTABLE_EXAMPLES`.

### Capability integration

**Target:** N/A — the Feature has one direct Requirement, so there is no cross-Requirement interaction to prove at this level.

### Capability validation

**Target:** N/A — safe import/inspection is already the complete Feature claim after the Feature wording is aligned with the normative Requirement; no separate intended-use validation target is declared.

## Goal · GOAL_DEVELOPER_USABILITY

**Capability support:** ALL direct Features deriving from {need}`GOAL_DEVELOPER_USABILITY`.

### Cross-capability integration

**Target:** N/A — package-root API resolution and example import safety are independent developer-consumption contracts; the Goal does not require runtime coordination, shared state, or data flow between the two Features.

### Outcome validation

**Target:** N/A — the Goal outcome is fully defined by its child contracts: the public surface resolves from the package root and examples remain safe to import and inspect. No separate operational/user scenario adds a distinct product claim here.
