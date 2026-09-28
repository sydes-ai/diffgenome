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
  attempt 1: rejected  model=gpt-5
    - 1 of 1 probe tests failed
    -       12 |     const logger = new Logger('customScope');
    -       13 |     logger.info('hello', 42);
    -     > 14 | 
    -          | ^
    -       15 |     expect(infoMock).toHaveBeenCalledTimes(1);
    -       16 |     expect(infoMock).toHaveBeenCalledWith('[customScope] hello', [42]);
    -       17 |   } finally {
- objective: internal_gap src/lib/logger/Logger.Logger.info (from src/api/services/PetService.PetService.create, d1)
  attempt 2: accepted  model=gpt-5
  learned 5 observed edge(s):
    + js:src/lib/logger/Logger.Logger.constructor → js:src/lib/logger/Logger.Logger.parsePathToScope [returned]
    + js:src/lib/logger/Logger.Logger.info → js:src/lib/logger/Logger.Logger.log [returned]
    + js:src/lib/logger/Logger.Logger.log → js:src/lib/logger/Logger.Logger.formatScope [returned]
    + js:test/unit/diffgenome_probe_0_2.test.ts::Logger.info delegates to winston with formatted scope and args array → js:src/lib/logger/Logger.Logger.constructor [returned]
    + js:test/unit/diffgenome_probe_0_2.test.ts::Logger.info delegates to winston with formatted scope and args array → js:src/lib/logger/Logger.Logger.info [returned]

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

## Behavioral map slice around the changed symbols

```
legend: → observed  ⇢ composed (join=symbol|arg_shape|value)  → [gap] internal gap  → [unresolved] stand-in not resolved  → [external] outside the repository  → [os] kernel boundary

# src/api/errors/InvalidPetAgeError.InvalidPetAgeError  [origin=unknown executed_by=0 outcomes={}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  (no observed or composed caller)
## downstream (what continues from it)
  (no observed continuation)

# src/api/errors/InvalidPetAgeError.InvalidPetAgeError.constructor  [origin=repo executed_by=1 outcomes={'returned': 2}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├src/api/services/PetService.PetService.create →  [observed outcomes=returned:2 tests=1]
  │  ├test/unit/services/PetService.test.<anon>@9.<anon>@11 →  [observed outcomes=raised:1,returned:1 tests=1]
  │  │  └test/unit/services/PetService.test.ts::PetService Create should dispatch subscribers →  [observed outcomes=returned:1 tests=1]
  │  └test/unit/services/PetService.test.<anon>@9.<anon>@24 →  [observed outcomes=raised:1,returned:1 tests=1]
  │     └test/unit/services/PetService.test.ts::PetService Create should reject a non-positive age →  [observed outcomes=returned:1 tests=1]
  └test/unit/services/PetService.test.<anon>@9.<anon>@24 →  [observed outcomes=returned:2 tests=1]
     └test/unit/services/PetService.test.ts::PetService Create should reject a non-positive age →  [observed outcomes=returned:1 tests=1]
## downstream (what continues from it)
  (no observed continuation)

# src/api/services/PetService.PetService.create  [origin=repo executed_by=2 outcomes={'returned': 1, 'raised': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├test/unit/services/PetService.test.<anon>@9.<anon>@11 →  [observed outcomes=raised:1,returned:1 tests=1]
  │  └test/unit/services/PetService.test.ts::PetService Create should dispatch subscribers →  [observed outcomes=returned:1 tests=1]
  └test/unit/services/PetService.test.<anon>@9.<anon>@24 →  [observed outcomes=raised:1,returned:1 tests=1]
     └test/unit/services/PetService.test.ts::PetService Create should reject a non-positive age →  [observed outcomes=returned:1 tests=1]
## downstream (what continues from it)
  ├⇢ src/lib/logger/Logger.Logger.info  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=3 probe-derived]
  │  └→ src/lib/logger/Logger.Logger.log  [observed outcomes=returned:1 tests=1 probe-derived]
  │     ├→ src/lib/logger/Logger.Logger.formatScope  [observed outcomes=returned:1 tests=1 probe-derived]
  │     └→ [unresolved] js:jest.fn  [unresolved_boundary rule=no-claim tests=1 probe-derived]
  ├→ src/api/errors/InvalidPetAgeError.InvalidPetAgeError.constructor  [observed outcomes=returned:2 tests=1]
  ├→ src/api/models/Pet.Pet.toString  [observed outcomes=returned:2 tests=2]
  ├→ [unresolved] js:test/unit/lib/EventDispatcherMock.EventDispatcherMock.dispatch  [unresolved_boundary rule=no-claim tests=1]
  └→ [unresolved] js:test/unit/lib/RepositoryMock.RepositoryMock.save  [unresolved_boundary rule=no-claim tests=1]
```

The full repo-level graph with every edge's provenance is `graph.json` next to this report (`graph-before.json` is the state before probes). Query it with `python -m diffgenome inspect --graph graph.json --symbol <id or suffix>`.
