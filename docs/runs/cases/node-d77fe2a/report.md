# diffgenome behavioral impact report

Change: git diff d77fe2a
Changed symbols (6):
  src/api/errors/InvalidPetAgeError.InvalidPetAgeError  executed by 0 test(s)  ← no existing execution
  src/api/errors/InvalidPetAgeError.InvalidPetAgeError.constructor  executed by 1 test(s)
  src/api/services/PetService.PetService.create  executed by 2 test(s)
  test/unit/services/PetService.test.<anon>@9  executed by 0 test(s)  ← no existing execution
  test/unit/services/PetService.test.<anon>@9.<anon>@11  executed by 1 test(s)
  test/unit/services/PetService.test.<anon>@9.<anon>@24  executed by 1 test(s)

## Behavioral neighborhood (before probes)

### Upstream (what reaches the change)
  d1  src/api/services/PetService.PetService.create → src/api/errors/InvalidPetAgeError.InvalidPetAgeError.constructor  tests=1
  d1  test/unit/services/PetService.test.<anon>@9.<anon>@11 → src/api/services/PetService.PetService.create  tests=1
  d1  test/unit/services/PetService.test.<anon>@9.<anon>@24 → src/api/errors/InvalidPetAgeError.InvalidPetAgeError.constructor  tests=1
  d1  test/unit/services/PetService.test.<anon>@9.<anon>@24 → src/api/services/PetService.PetService.create  tests=1
  d2  test/unit/services/PetService.test.ts::PetService Create should dispatch subscribers → test/unit/services/PetService.test.<anon>@9.<anon>@11  tests=1
  d2  test/unit/services/PetService.test.ts::PetService Create should reject a non-positive age → test/unit/services/PetService.test.<anon>@9.<anon>@24  tests=1

### Downstream (what continues from the change)
  d1  src/api/services/PetService.PetService.create → src/api/models/Pet.Pet.toString  tests=2
  d1  src/api/services/PetService.PetService.create → [gap] src/lib/logger/Logger.Logger.info  tests=2  rule=claim-member
  d1  src/api/services/PetService.PetService.create → [unresolved] js:test/unit/lib/EventDispatcherMock.EventDispatcherMock.dispatch  tests=1  rule=no-claim
  d1  src/api/services/PetService.PetService.create → [unresolved] js:test/unit/lib/RepositoryMock.RepositoryMock.save  tests=1  rule=no-claim

### Tests establishing these paths (2)
  test/unit/services/PetService.test.ts::PetService Create should dispatch subscribers
  test/unit/services/PetService.test.ts::PetService Create should reject a non-positive age

## Where knowledge stops (before probes)
### internal_gap (1)
  d1  src/api/services/PetService.PetService.create → [gap] src/lib/logger/Logger.Logger.info  tests=2  rule=claim-member
### unresolved_boundary (2)
  d1  src/api/services/PetService.PetService.create → [unresolved] js:test/unit/lib/EventDispatcherMock.EventDispatcherMock.dispatch  tests=1  rule=no-claim
  d1  src/api/services/PetService.PetService.create → [unresolved] js:test/unit/lib/RepositoryMock.RepositoryMock.save  tests=1  rule=no-claim

## Generated probes
- objective: internal_gap src/lib/logger/Logger.Logger.info (from src/api/services/PetService.PetService.create, d1)
  attempt 1: accepted  model=recorded
  learned 5 observed edge(s):
    + js:src/lib/logger/Logger.Logger.constructor → js:src/lib/logger/Logger.Logger.parsePathToScope [returned]
    + js:src/lib/logger/Logger.Logger.info → js:src/lib/logger/Logger.Logger.log [returned]
    + js:src/lib/logger/Logger.Logger.log → js:src/lib/logger/Logger.Logger.formatScope [returned]
    + js:test/unit/diffgenome_probe_0_1.test.ts::Logger.info delegates to winston with formatted scope and args array → js:src/lib/logger/Logger.Logger.constructor [returned]
    + js:test/unit/diffgenome_probe_0_1.test.ts::Logger.info delegates to winston with formatted scope and args array → js:src/lib/logger/Logger.Logger.info [returned]

## Before vs after
| metric | before | after |
|---|---|---|
| observed edges | 7 | 9 |
| composed edges | 0 | 1 |
| strong joins (VALUE+) | 0 | 0 |
| weak joins | 0 | 1 |
| internal gaps | 1 | 0 |
| unresolved boundaries | 2 | 3 |
| external boundaries | 0 | 0 |
| os boundaries | 0 | 0 |
| unsound attempts | 0 | 0 |
| probe-derived edges | 0 | 4 |
| symbols | 11 | 14 |
| tests | 2 | 3 |
| reconstructed / provisional denominator | 7/10 = 0.700 | 9/13 = 0.692 |

Denominator is provisional: observed + composed edges + internal gaps + unresolved
stand-ins inside the neighborhood, i.e. the seams we know about. It excludes behavior
no execution has come near, and external/OS boundaries, which are terminal by design.

## Remaining after probes
### internal_gap (0)
### unresolved_boundary (3)
  d1  src/api/services/PetService.PetService.create → [unresolved] js:test/unit/lib/EventDispatcherMock.EventDispatcherMock.dispatch  tests=1  rule=no-claim
  d1  src/api/services/PetService.PetService.create → [unresolved] js:test/unit/lib/RepositoryMock.RepositoryMock.save  tests=1  rule=no-claim
  d3  src/lib/logger/Logger.Logger.log → [unresolved] js:jest.fn  tests=1  rule=no-claim  probe-derived
### weak joins (1)
  d1  src/api/services/PetService.PetService.create ⇢ src/lib/logger/Logger.Logger.info  tests=3  join=arg_shape  rule=claim-member  probe-derived

## Notes
- 1 changed symbol(s) have no existing execution at all: src/api/errors/InvalidPetAgeError.InvalidPetAgeError

## Behavioral map around the changed symbols

```
legend: → observed continuation  ⇢ composed continuation (grade)  [external] outside the repo  [unresolved] stand-in without a resolution  [gap] internal continuation nobody has executed  [declaration] construction/declaration with no in-repo executable body

# src/api/errors/InvalidPetAgeError.InvalidPetAgeError   [changed declaration: no executable body of its own]

# src/api/errors/InvalidPetAgeError.InvalidPetAgeError.constructor   [changed; outcomes={'returned': 2}; reached by: tests 1: test/unit/services/PetService.test.ts::PetService Create should reject a non-positive age]
## reaches the change
  └src/api/services/PetService.PetService.create  [entrypoint] → this
        evidence: observed 1 exec · tests 1
        reached by: tests 2: test/unit/services/PetService.test.ts::PetService Create should dispatch subscribers, test/unit/services/PetService.test.ts::PetService Create should reject a non-positive age
## continues from the change
  (no continuation observed)

# src/api/services/PetService.PetService.create   [changed; outcomes={'returned': 1, 'raised': 1}; reached by: tests 2: test/unit/services/PetService.test.ts::PetService Create should dispatch subscribers, test/unit/services/PetService.test.ts::PetService Create should reject a non-positive age]
## reaches the change
  (no production caller observed or composed; only tests/probes call it directly)
## continues from the change
  ├→ src/api/errors/InvalidPetAgeError.InvalidPetAgeError.constructor
  │     evidence: observed 1 exec · tests 1
  ├→ src/api/models/Pet.Pet.toString
  │     evidence: observed 2 exec · tests 2
  ├⇢ src/lib/logger/Logger.Logger.info (ARG_SHAPE)
  │     evidence: composed ARG_SHAPE x2 · rule=claim-member · tests 2 · probes 1
  │  └→ src/lib/logger/Logger.Logger.log
  │        evidence: observed 1 exec · tests 0 · probes 1
  │     ├→ src/lib/logger/Logger.Logger.formatScope
  │     │     evidence: observed 1 exec · tests 0 · probes 1
  │     └→ [unresolved] js:jest.fn
  │           evidence: rule=no-claim · tests 0 · probes 1
  ├→ [unresolved] js:test/unit/lib/EventDispatcherMock.EventDispatcherMock.dispatch
  │     evidence: rule=no-claim · tests 1
  └→ [unresolved] js:test/unit/lib/RepositoryMock.RepositoryMock.save
        evidence: rule=no-claim · tests 1

```

The full repo-level graph with every edge's provenance is `graph.json` next to this report (`graph-before.json` is the state before probes). Query it with `python -m diffgenome inspect --graph graph.json --symbol <id or suffix>`.
