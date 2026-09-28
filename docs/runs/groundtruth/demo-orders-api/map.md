legend: → observed  ⇢ composed (join=symbol|arg_shape|value)  → [gap] internal gap  → [unresolved] stand-in not resolved  → [external] outside the repository  → [os] kernel boundary

# app.main.create_order  [origin=repo executed_by=1 outcomes={'returned': 1, 'raised': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  └tests.test_diffgenome_probe_0_1.test_probe_create_order_executes_and_handles_unknown_sku →  [observed outcomes=raised:1,returned:1 tests=1 probe-derived]
## downstream (what continues from it)
  ├⇢ app.service.create_order  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  ├⇢ app.repository.save_order  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  │  └→ [external] pydantic.main.BaseModel.__init__  [external_boundary rule=claim-outside-repo tests=1 probe-derived]
  │  └⇢ app.service.get_stock  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │     └⇢ app.repository.get_stock  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │        └→ [unresolved] builtins.dict  [unresolved_boundary rule=claim-unknown-origin tests=1 probe-derived]
  └→ [gap] app.service.create_order  [internal_gap rule=claim-member tests=1 probe-derived]

# app.service.create_order  [origin=repo executed_by=1 outcomes={'returned': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├app.main.create_order ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  └tests.test_diffgenome_probe_0_1.test_probe_create_order_executes_and_handles_unknown_sku →  [observed outcomes=raised:1,returned:1 tests=1 probe-derived]
  └tests.test_diffgenome_probe_1_1.test_create_order_invokes_inventory_and_persists →  [observed outcomes=returned:1 tests=1 probe-derived]
## downstream (what continues from it)
  ├⇢ app.repository.save_order  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]  (see above)
  └⇢ app.service.get_stock  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]  (see above)

# app.service.get_stock  [origin=repo executed_by=1 outcomes={'returned': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├app.main.read_inventory ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  └tests.test_diffgenome_probe_5_1.test_read_inventory_calls_get_stock_and_returns_item →  [observed outcomes=returned:1 tests=1 probe-derived]
  ├app.service.create_order ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  ├app.main.create_order ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  │  └tests.test_diffgenome_probe_0_1.test_probe_create_order_executes_and_handles_unknown_sku →  [observed outcomes=raised:1,returned:1 tests=1 probe-derived]
  │  └tests.test_diffgenome_probe_1_1.test_create_order_invokes_inventory_and_persists →  [observed outcomes=returned:1 tests=1 probe-derived]
  └tests.test_diffgenome_probe_2_1.test_get_stock_calls_repository_and_returns_value →  [observed outcomes=returned:1 tests=1 probe-derived]
## downstream (what continues from it)
  └⇢ app.repository.get_stock  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]  (see above)

# app.repository.get_stock  [origin=repo executed_by=1 outcomes={'returned': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├app.service.get_stock ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  ├app.main.read_inventory ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  │  └tests.test_diffgenome_probe_5_1.test_read_inventory_calls_get_stock_and_returns_item →  [observed outcomes=returned:1 tests=1 probe-derived]
  │  ├app.service.create_order ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  │  ├app.main.create_order ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  │  └tests.test_diffgenome_probe_1_1.test_create_order_invokes_inventory_and_persists →  [observed outcomes=returned:1 tests=1 probe-derived]
  │  └tests.test_diffgenome_probe_2_1.test_get_stock_calls_repository_and_returns_value →  [observed outcomes=returned:1 tests=1 probe-derived]
  └tests.test_diffgenome_probe_3_1.test_get_stock_reads_from_inventory →  [observed outcomes=returned:1 tests=1 probe-derived]
## downstream (what continues from it)
  └→ [unresolved] builtins.dict  [unresolved_boundary rule=claim-unknown-origin tests=1 probe-derived]  (see above)

# app.repository.save_order  [origin=repo executed_by=1 outcomes={'returned': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├app.service.create_order ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  ├app.main.create_order ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  │  └tests.test_diffgenome_probe_0_1.test_probe_create_order_executes_and_handles_unknown_sku →  [observed outcomes=raised:1,returned:1 tests=1 probe-derived]
  │  └tests.test_diffgenome_probe_1_1.test_create_order_invokes_inventory_and_persists →  [observed outcomes=returned:1 tests=1 probe-derived]
  └tests.test_diffgenome_probe_4_1.test_probe_save_order_spies_on_order_ctor_and_appends →  [observed outcomes=returned:1 tests=1 probe-derived]
## downstream (what continues from it)
  └→ [external] pydantic.main.BaseModel.__init__  [external_boundary rule=claim-outside-repo tests=1 probe-derived]  (see above)

# app.main.read_inventory  [origin=repo executed_by=1 outcomes={'returned': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  └tests.test_diffgenome_probe_5_1.test_read_inventory_calls_get_stock_and_returns_item →  [observed outcomes=returned:1 tests=1 probe-derived]
## downstream (what continues from it)
  └⇢ app.service.get_stock  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
     └⇢ app.repository.get_stock  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]  (see above)
