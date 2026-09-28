legend: → observed continuation  ⇢ composed continuation (grade)  [external] outside the repo  [unresolved] stand-in without a resolution  [gap] internal continuation nobody has executed  [declaration] construction/declaration with no in-repo executable body

# app.main.create_order   [changed; outcomes={'returned': 1, 'raised': 1}; reached by: probes 1]
## reaches the change
  (no production caller observed or composed; only tests/probes call it directly)
## continues from the change
  └⇢ app.service.create_order (ARG_SHAPE)
        evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 0 · probes 2
     ├⇢ app.repository.save_order (ARG_SHAPE)
     │     evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 0 · probes 2
     │  └→ [external] pydantic.main.BaseModel.__init__
     │        evidence: rule=claim-outside-repo · tests 0 · probes 1
     └⇢ app.service.get_stock (ARG_SHAPE)
           evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 0 · probes 2
        └⇢ app.repository.get_stock (ARG_SHAPE)
              evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 0 · probes 2
           └→ [unresolved] builtins.dict
                 evidence: rule=claim-unknown-origin · tests 0 · probes 1

# app.service.create_order   [changed; outcomes={'returned': 1}; reached by: probes 1]
## reaches the change
  └app.main.create_order  [entrypoint] ⇢ (ARG_SHAPE) this
        evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 0 · probes 2
        reached by: probes 1
## continues from the change
  ├⇢ app.repository.save_order (ARG_SHAPE)  (see above)
  └⇢ app.service.get_stock (ARG_SHAPE)  (see above)

# app.service.get_stock   [changed; outcomes={'returned': 1}; reached by: probes 1]
## reaches the change
  ├app.main.read_inventory  [entrypoint] ⇢ (ARG_SHAPE) this
  │     evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 0 · probes 2
  │     reached by: probes 1
  └app.service.create_order ⇢ (ARG_SHAPE) this
        evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 0 · probes 2
     └app.main.create_order  [entrypoint] ⇢ (ARG_SHAPE) this
           evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 0 · probes 2
           reached by: probes 1
## continues from the change
  └⇢ app.repository.get_stock (ARG_SHAPE)  (see above)

# app.repository.get_stock   [changed; outcomes={'returned': 1}; reached by: probes 1]
## reaches the change
  └app.service.get_stock ⇢ (ARG_SHAPE) this
        evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 0 · probes 2
     ├app.main.read_inventory  [entrypoint] ⇢ (ARG_SHAPE) this
     │     evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 0 · probes 2
     │     reached by: probes 1
     └app.service.create_order ⇢ (ARG_SHAPE) this
           evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 0 · probes 2
        └app.main.create_order  [entrypoint] ⇢ (ARG_SHAPE) this
              evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 0 · probes 2
              reached by: probes 1
## continues from the change
  └→ [unresolved] builtins.dict  (see above)

# app.repository.save_order   [changed; outcomes={'returned': 1}; reached by: probes 1]
## reaches the change
  └app.service.create_order ⇢ (ARG_SHAPE) this
        evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 0 · probes 2
     └app.main.create_order  [entrypoint] ⇢ (ARG_SHAPE) this
           evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 0 · probes 2
           reached by: probes 1
## continues from the change
  └→ [external] pydantic.main.BaseModel.__init__  (see above)

# app.main.read_inventory   [changed; outcomes={'returned': 1}; reached by: probes 1]
## reaches the change
  (no production caller observed or composed; only tests/probes call it directly)
## continues from the change
  └⇢ app.service.get_stock (ARG_SHAPE)
        evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 0 · probes 2
     └⇢ app.repository.get_stock (ARG_SHAPE)  (see above)

