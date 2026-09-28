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
