(assurance-profile-data-safety)=

# Assurance profile · Data safety

**Scope:** {need}`GOAL_DATA_SAFETY` and its direct Feature branch.

**Policy:** {ref}`Upper-level assurance and validation <test-plan-upper-level-assurance>`

This profile declares only upper-level Targets that cannot be reduced to one child
Requirement or Technical requirement. Child-support gates come from the authoritative
Sphinx-Needs `derives` graph.

## Feature · FEAT_SENSITIVE_DATA_PROTECTION

**Requirement support:** ALL direct Requirements deriving from
{need}`FEAT_SENSITIVE_DATA_PROTECTION`.

### Capability integration

**Target:** N/A — the Feature currently has one direct Requirement, so there is no
cross-Requirement interaction to prove at this level. Technical interaction among its
derived logging/VCR obligations is owned by the parent Requirement through required
technical support.

### Capability validation

**Target:** N/A — the Feature claim is the same confidentiality outcome already proven
by {need}`REQ_SENSITIVE_DATA_PROTECTION`. Adding a second Feature-level copy would
duplicate Requirement evidence rather than validate a distinct intended-use claim.

## Goal · GOAL_DATA_SAFETY

**Capability support:** ALL direct Features deriving from {need}`GOAL_DATA_SAFETY`.

### Cross-capability integration

**Target:** N/A — the Goal currently has one direct Feature, so there is no cross-Feature
interaction to prove at this level.

### Outcome validation

**Target:** N/A — the Goal has one Feature whose parent Requirement already owns the
representative cross-artifact observability audit. No separate Goal-level operational
scenario is declared until the Goal gains a distinct outcome that cannot be reduced to
that child proof.
