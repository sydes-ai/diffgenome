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

