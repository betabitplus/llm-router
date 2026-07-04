## v0.8.1 (2026-07-04)

### Fix

- promote repository rename sync
- sync repository rename references

## v0.8.0 (2026-05-08)

### Feat

- add reusable operation duration logging
- add private internal runtime

### Refactor

- move config install lifecycle internal
- refine config API boundary

## v0.7.4 (2026-05-04)

### Refactor

- improve repo portability
- prepare repo scaffolding for reuse

## v0.7.3 (2026-04-17)

### Refactor

- guard private-core boundaries

## v0.7.2 (2026-04-17)

### Refactor

- **e2e**: align verification slices with architecture concepts

## v0.7.1 (2026-04-14)

### Fix

- upgrade pillow to 12.2

### Refactor

- **workbench**: reorganize helpers and refresh probes

## v0.7.0 (2026-04-08)

### Feat

- add pytest-xdist to dependencies and enable parallel test execution in pre-commit hooks
- **providers**: add tool and media capability coverage
- **qwenchat**: add direct tool and video workbench flows
- **probes**: add executable third-party dependency probes

### Fix

- appease pyright for executor init
- type-safe sync attempt executor
- deflake attempt-timeout e2e under CI
- **qwenchat**: document tool loop request shape
- **qwenchat**: satisfy push hook
- **workbench**: satisfy pyright push hook
- **workbench**: validate live provider scripts
- **aistudio**: satisfy native video type checks
- **hooks**: align local parity with ci
- **routing**: extract route logging helpers
- **probes**: satisfy console type checks
- **scripts**: remove llm_router dependency from genai model script
- **routing**: record blocked wait in routing trace
- **config**: restore facade boundaries
- **config**: satisfy pyright config checks
- **vcr**: accept urlsafe inline media
- **vcr**: normalize embedded binary payloads
- **vcr**: normalize wrapped base64 media
- **vcr**: stabilize json media matching
- **tests**: load nvidia key via shared resolver

### Refactor

- **dev**: switch to direnv-only environment setup
- **workbench**: move provider probes into workbench
- **workbench**: simplify provider helper structure
- **workbench**: normalize provider script matrix
- **config**: align config contracts and defaults
- **support**: simplify shared formatting infra
- **exceptions**: tighten exception contract
- **routing**: reuse shared duration helper
- **support**: simplify logging helpers
- **logging**: standardize structured logging contract
- **api**: simplify public facade internals
- **tests**: organize llm_router support helpers
- **tests**: reorganize shared support helpers
- **tests**: move llm_router fault server
- **tests**: improve demo console output
- **workbench**: nest provider scripts under llm_router
- **workbench**: replace probes and unify direct-run setup
- **probes**: simplify live dependency demos
- **config**: split defaults from config facade
- separate public facade from private core

## v0.6.6 (2026-03-05)

### Fix

- resolve CI lint and hook drift

## v0.6.5 (2026-03-04)

### Fix

- restore release workflow to pre-migration behavior
- avoid secrets context in workflow if condition
- restore automatic release version bump
- skip releases when version is unchanged
- fail release when version tag points to another commit
- make release workflow compatible with protected main

## v0.6.4 (2026-03-04)

### Fix

- restore release workflow to pre-migration behavior
- avoid secrets context in workflow if condition
- restore automatic release version bump
- skip releases when version is unchanged
- fail release when version tag points to another commit
- make release workflow compatible with protected main

### Refactor

- migrate to llm-router standalone package

## v0.6.3 (2026-03-04)

### Refactor

- **llm_router**: unify public contracts and add __version__
- **llm_router**: organize schemas and simplify validators
- **llm_router**: simplify config and test setup
- remove core module and simplify logging

## v0.6.2 (2026-03-02)

### Refactor

- **config**: simplify config management

## v0.6.1 (2026-03-01)

### Fix

- **tests**: stabilize VCR replay
- **ci**: make VCR replay hermetic
- **packaging**: include VCR serializer in sdist
- **tests**: make VCR YAML serializer bandit-safe
- **tests**: commit VCR cassettes and stabilize YAML

### Refactor

- **tests**: simplify VCR matching
- **tests**: organize VCR infrastructure
