# Task: propose the semantic layer of a Behavioral Genome for a stateful component

You are an abstraction engine. The component is `ModelManager` in Kokoro-FastAPI
(api/src/inference/model_manager.py): it loads, unloads and lazily re-initializes a model
backend, counts active requests, and schedules an idle-unload timer. Its behavior depends on
internal state and changes that state.

Deterministic machinery has ALREADY established the mechanics below. Do not re-derive them
and do not contradict them:
- every decision site (`if`) with a stable id `br:...`, its source predicate, the origins
  of its operands (local def-use), and the (site, outcome) pairs required to reach it;
- for every call and field store: which (site, outcome) pairs it requires;
- for the tests shown: the ordered event log of manager calls, the observed outcome of every
  decision site (T/F), and the bucketed state of the manager before and after each call
  (value-free buckets: none, obj:<Type>, obj:stand-in, num:zero/pos/neg, bool:true/false).

Your job is MEANING: name the state that matters, abstract the predicates, and give compact
rules that GENERATE the observed behavior, including behavior that depends on state set
by an earlier call. A machine will check everything you cite and assign status; you assign
none. Some tests' traces are withheld (listed below); you still see their source, and you
must write scenarios for them — they will be predicted from your genome and compared with
what actually executed.

Return ONLY one JSON object:

{
 "variables": [{"id", "name", "origin": "state|setting|input|derived", "description",
                "observed_as": {"fact": "<state fact name, e.g. self._backend or global.settings.model_auto_unload_timeout_seconds>",
                                "kind": "is_set|sign|bool"} | null,
                "definition": "<predicate over other variables>" | null,
                "evidence": [...]}],
 "decisions": [{"id", "entity": "<method, e.g. ModelManager.ensure_backend>", "site": "br:...",
                "inputs": [...], "predicate": "<over variable names>", "order": <int>,
                "true_branch":  {"steps": [...], "calls": [...], "absent": [...], "stops": bool, "effect": "..."},
                "false_branch": {...}, "evidence": [...]}],
 "transitions": [{"id", "entity": "<method>", "when": "<predicate or true>", "sets": {"<variable>": "<expr>"},
                  "state_before", "action", "state_after", "evidence": [...]}],
 "procedures": [{"id", "entity": "<method>", "steps": ["call:<method>", "T:<transition id>", "D:<decision id>", ...],
                 "evidence": [...]}],
 "rules": [{"id", "name", "inputs", "relevant_state", "condition", "consequences": [...], "decision": "<id>|null", "evidence": [...]}],
 "regimes": [{"id", "name", "facts": {...}, "members": ["<test name>"], "evidence": [...]}],
 "scenarios": {"<test name>": {"state": {<variable>: value}, "calls": [{"entity": "<method>", "facts": {<variable>: value}}]}},
 "unknowns": [{"what", "why"}]
}

Semantics used by the predictor:
- A call of an entity runs its procedure's steps in order. "call:X" records a call and, if X
  has a procedure, runs it; "T:id" applies a transition (if `when` holds, each variable in
  `sets` becomes the expression: literals true/false/none/integers, `var`, `!var`,
  `var + k`, `var - k`, `max(0, var - k)`); "D:id" evaluates a decision and runs the taken
  branch's `steps` (or, if empty, its `calls` as "call:" steps); a branch with `stops: true`
  ends the entity. Decisions evaluate `predicate` over the current variable values
  (booleans/integers; `!name`, comparisons, `&&`, `||`, no parentheses).
- Variables bound with `observed_as` are compared with the observed bucketed state
  (is_set: bucket != none; sign: num:zero/pos/neg as 0/positive/negative; bool).
- A scenario's `state` is the state the test establishes before its first manager call
  (including direct assignments like `manager._backend = MagicMock()` and settings set by
  monkeypatch); `calls` are the test's top-level manager calls and external events in
  order (e.g. an idle timer firing after `await asyncio.sleep(...)` is a call of
  `ModelManager._idle_unload_after`). The predicted decision outcomes must equal the
  observed outcomes at your decision sites, in order, and the predicted final values of
  bound variables must equal the observed final state.
- Use only the site ids given. Evidence ref kinds (JSON):
  {"kind":"source","file":"api/src/inference/model_manager.py","line":N,"text":"<exact text>"}
  {"kind":"branch","site":"br:...","test":"<shown test name>","outcome":true|false}
  {"kind":"control","site":"br:...","outcome":true|false,"callee":"<call expression or method>"}
  {"kind":"dataflow","site":"br:...","origin":"<e.g. param:self._backend>"}
  {"kind":"delta","entity":"<method>","fact":"self._backend","before":"obj:stand-in","after":"none","test":"<shown test name>"}
  {"kind":"store","entity":"<method>","path":"self._backend"}
  Cite only shown tests in evidence.
- Prefer few, generative rules. Be honest in `unknowns` about what the evidence cannot settle.

## Mechanics (deterministic, intra-procedural)

### ModelManager.__init__
- call `asyncio.Lock` line 33 requires: —
- store `self._config` ← global:model_config, param:config line 30 requires: —
- store `self._backend` ← const line 31 requires: —
- store `self._device` ← const line 32 requires: —
- store `self._lock` ← call:asyncio.Lock line 33 requires: —
- store `self._active_requests` ← const line 34 requires: —
- store `self._last_used_at` ← const line 35 requires: —
- store `self._idle_unload_task` ← const line 36 requires: —

### ModelManager._determine_device
(no decision site, no field store)

### ModelManager.initialize
- call `self._determine_device` line 45 requires: —
- call `logger.info` line 46 requires: —
- call `KokoroV1` line 47 requires: —
- call `RuntimeError` line 50 requires: ?exception-handler
- store `self._device` ← call:self._determine_device line 45 requires: —
- store `self._backend` ← call:KokoroV1 line 47 requires: —

### ModelManager.initialize_with_warmup
(no decision site, no field store)

### ModelManager.ensure_backend
- site br:1f44d4f2492f line 111: `self._backend` | operands: self._backend ← param:self._backend | requires: — | then-block exits: True, else-block exits: False
- site br:2c6c7a26afe6 line 114: `not self._backend` | operands: self._backend ← param:self._backend | requires: br:1f44d4f2492f=F | then-block exits: False, else-block exits: False
- call `self._cancel_idle_unload_timer` line 115 requires: br:1f44d4f2492f=F & br:2c6c7a26afe6=T
- call `self.initialize` line 116 requires: br:1f44d4f2492f=F & br:2c6c7a26afe6=T
- call `self.load_model` line 117 requires: br:1f44d4f2492f=F & br:2c6c7a26afe6=T

### ModelManager.get_backend
- site br:5ea6e7329f80 line 128: `not self._backend` | operands: self._backend ← param:self._backend | requires: — | then-block exits: True, else-block exits: False
- call `RuntimeError` line 129 requires: br:5ea6e7329f80=T

### ModelManager.load_model
- site br:34208645b556 line 141: `not self._backend` | operands: self._backend ← param:self._backend | requires: — | then-block exits: True, else-block exits: False
- call `RuntimeError` line 142 requires: br:34208645b556=T
- call `self._backend.load_model` line 145 requires: br:34208645b556=F
- call `time.monotonic` line 146 requires: br:34208645b556=F
- call `self._schedule_idle_unload_timer_locked` line 147 requires: br:34208645b556=F
- call `RuntimeError` line 151 requires: br:34208645b556=F & ?exception-handler
- store `self._last_used_at` ← call:time.monotonic line 146 requires: br:34208645b556=F

### ModelManager._auto_unload_timeout
(no decision site, no field store)

### ModelManager._format_seconds
(no decision site, no field store)

### ModelManager._auto_unload_enabled
(no decision site, no field store)

### ModelManager._cancel_idle_unload_timer
- site br:be9c978e2166 line 167: `self._idle_unload_task and (not self._idle_unload_task.done()) and (self._idle_unload_task is not current_task)` | operands: current_task ← call:asyncio.current_task, const; self._idle_unload_task ← param:self._idle_unload_task | requires: — | then-block exits: False, else-block exits: False
- call `asyncio.current_task` line 164 requires: —
- call `self._idle_unload_task.done` line 169 requires: —
- call `self._idle_unload_task.cancel` line 172 requires: br:be9c978e2166=T
- store `self._idle_unload_task` ← const line 173 requires: —

### ModelManager._unload_backend_locked
- site br:e6f07b6d711d line 176: `self._backend is None` | operands: self._backend ← param:self._backend | requires: — | then-block exits: True, else-block exits: False
- call `self._backend.unload` line 178 requires: br:e6f07b6d711d=F
- call `time.monotonic` line 180 requires: br:e6f07b6d711d=F
- store `self._backend` ← const line 179 requires: br:e6f07b6d711d=F
- store `self._last_used_at` ← call:time.monotonic line 180 requires: br:e6f07b6d711d=F

### ModelManager._schedule_idle_unload_timer_locked
- site br:075bba2b9a54 line 185: `not self._auto_unload_enabled() or self._backend is None or self._active_requests > 0` | operands: self ← param:self; self._active_requests ← param:self._active_requests; self._backend ← param:self._backend | requires: — | then-block exits: True, else-block exits: False
- call `self._cancel_idle_unload_timer` line 184 requires: —
- call `self._auto_unload_enabled` line 186 requires: —
- call `self._auto_unload_timeout` line 192 requires: br:075bba2b9a54=F
- call `self._idle_unload_after` line 193 requires: br:075bba2b9a54=F
- call `asyncio.create_task` line 193 requires: br:075bba2b9a54=F
- store `self._idle_unload_task` ← call:asyncio.create_task, call:self._auto_unload_timeout, call:self._idle_unload_after, global:asyncio, param:self line 193 requires: br:075bba2b9a54=F

### ModelManager._idle_unload_after
- site br:79d02f610d4d line 199: `not self._auto_unload_enabled() or self._backend is None or self._active_requests > 0 or (self._last_used_at is None)` | operands: self ← param:self; self._active_requests ← param:self._active_requests; self._backend ← param:self._backend; self._last_used_at ← param:self._last_used_at | requires: — | then-block exits: True, else-block exits: False
- site br:bad1968a9b60 line 208: `idle_for < self._auto_unload_timeout()` | operands: idle_for ← call:time.monotonic, global:time, param:self._last_used_at; self ← param:self | requires: br:79d02f610d4d=F | then-block exits: True, else-block exits: False
- site br:ed05503f84fe line 214: `unloaded` | operands: unloaded ← call:self._unload_backend_locked | requires: — | then-block exits: False, else-block exits: False
- site br:9eca4b37c953 line 215: `torch.cuda.is_available()` | operands: torch.cuda ← global:torch.cuda | requires: br:ed05503f84fe=T | then-block exits: False, else-block exits: False
- call `asyncio.sleep` line 197 requires: —
- call `self._auto_unload_enabled` line 200 requires: —
- call `time.monotonic` line 207 requires: br:79d02f610d4d=F
- call `self._auto_unload_timeout` line 208 requires: br:79d02f610d4d=F
- call `self._schedule_idle_unload_timer_locked` line 209 requires: br:79d02f610d4d=F & br:bad1968a9b60=T
- call `self._unload_backend_locked` line 212 requires: br:79d02f610d4d=F & br:bad1968a9b60=F
- call `torch.cuda.is_available` line 215 requires: br:ed05503f84fe=T
- call `torch.cuda.empty_cache` line 216 requires: br:ed05503f84fe=T & br:9eca4b37c953=T
- call `self._auto_unload_timeout` line 219 requires: br:ed05503f84fe=T
- call `self._format_seconds` line 219 requires: br:ed05503f84fe=T
- call `logger.info` line 217 requires: br:ed05503f84fe=T

### ModelManager._begin_request
- call `self._cancel_idle_unload_timer` line 227 requires: —
- store `self._active_requests` ← param:self._active_requests line 226 requires: —

### ModelManager._end_request
- call `max` line 231 requires: —
- call `time.monotonic` line 232 requires: —
- call `self._schedule_idle_unload_timer_locked` line 233 requires: —
- store `self._active_requests` ← call:max line 231 requires: —
- store `self._last_used_at` ← call:time.monotonic line 232 requires: —

### ModelManager.hold
(no decision site, no field store)

### ModelManager.generate
- site br:1ae6dab118b9 line 254: `settings.default_volume_multiplier != 1.0` | operands: settings.default_volume_multiplier ← global:settings.default_volume_multiplier | requires: ?loop | then-block exits: False, else-block exits: False
- call `self.hold` line 250 requires: —
- call `self.ensure_backend` line 251 requires: —
- call `self._backend.generate` line 253 requires: —
- call `RuntimeError` line 258 requires: ?exception-handler
- store `chunk.audio` ← global:settings.default_volume_multiplier, unknown:UNKNOWN_DEPENDENCE:loop-variable line 255 requires: ?loop & br:1ae6dab118b9=T

### ModelManager.unload_all
- site br:60ebe4954dd3 line 263: `self._backend` | operands: self._backend ← param:self._backend | requires: — | then-block exits: False, else-block exits: False
- call `self._cancel_idle_unload_timer` line 262 requires: —
- call `self._backend.unload` line 264 requires: br:60ebe4954dd3=T
- store `self._backend` ← const line 265 requires: br:60ebe4954dd3=T

### ModelManager.unload
- site br:4e5a06d4451e line 272: `torch.cuda.is_available()` | operands: torch.cuda ← global:torch.cuda | requires: — | then-block exits: False, else-block exits: False
- call `self._cancel_idle_unload_timer` line 270 requires: —
- call `self._unload_backend_locked` line 271 requires: —
- call `torch.cuda.is_available` line 272 requires: —
- call `torch.cuda.empty_cache` line 273 requires: br:4e5a06d4451e=T
- call `logger.info` line 274 requires: —

### ModelManager.reload
(no decision site, no field store)

### ModelManager.status
- site br:a08083f9aeea line 291: `self._last_used_at is not None` | operands: self._last_used_at ← param:self._last_used_at | requires: — | then-block exits: False, else-block exits: False
- site br:cfda31c8127c line 293: `self._auto_unload_enabled() and self._backend is not None` | operands: self ← param:self; self._backend ← param:self._backend | requires: br:a08083f9aeea=T | then-block exits: False, else-block exits: False
- call `self._auto_unload_timeout` line 288 requires: —
- call `time.monotonic` line 292 requires: br:a08083f9aeea=T
- call `max` line 292 requires: br:a08083f9aeea=T
- call `self._auto_unload_enabled` line 293 requires: br:a08083f9aeea=T
- call `max` line 294 requires: br:a08083f9aeea=T & br:cfda31c8127c=T
- call `self._auto_unload_enabled` line 300 requires: —

### ModelManager.current_backend
(no decision site, no field store)

### get_manager
- site br:2f19fdb911a4 line 321: `ModelManager._instance is None` | operands: ModelManager._instance ← global:ModelManager._instance | requires: — | then-block exits: False, else-block exits: False
- call `ModelManager` line 322 requires: br:2f19fdb911a4=T
- store `ModelManager._instance` ← call:ModelManager line 322 requires: br:2f19fdb911a4=T

## Observed event logs (shown tests)

Manager calls in chronological order, indented by manager call depth, each decision site's observed outcome where it was evaluated, the manager's bucketed state on entry, and the observed state deltas (Δ) on exit. Calls into non-manager code are looked through.

```
### test_active_request_blocks_idle_unload
call ModelManager.__init__  [returned]  state-in: —  Δ self._config: ∅→obj:ModelConfig; self._backend: ∅→none; self._device: ∅→none; self._lock: ∅→obj:Lock; self._active_requests: ∅→num:zero; self._last_used_at: ∅→none; self._idle_unload_task: ∅→none
call ModelManager.generate  [returned]  state-in: global.settings.default_volume_multiplier=num:pos, self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none  Δ self._last_used_at: none→num:pos; self._idle_unload_task: none→obj:Task
  call ModelManager.hold  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none  Δ self._last_used_at: none→num:pos; self._idle_unload_task: none→obj:Task
    call ModelManager._begin_request  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none  Δ self._active_requests: num:zero→num:pos
      call ModelManager._cancel_idle_unload_timer  [returned]  state-in: self._active_requests=num:pos, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none
        branch br:be9c978e2166 `self._idle_unload_task and (not self._idle_unload_task.done()) and (se` = F
  call ModelManager.ensure_backend  [returned]  state-in: self._active_requests=num:pos, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none
    branch br:1f44d4f2492f `self._backend` = T
  branch br:1ae6dab118b9 `settings.default_volume_multiplier != 1.0` = F
    call ModelManager._end_request  [returned]  state-in: self._active_requests=num:pos, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none  Δ self._active_requests: num:pos→num:zero; self._last_used_at: none→num:pos; self._idle_unload_task: none→obj:Task
      call ModelManager._schedule_idle_unload_timer_locked  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos  Δ self._idle_unload_task: none→obj:Task
        call ModelManager._cancel_idle_unload_timer  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
          branch br:be9c978e2166 `self._idle_unload_task and (not self._idle_unload_task.done()) and (se` = F
        call ModelManager._auto_unload_enabled  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
          call ModelManager._auto_unload_timeout  [returned]  state-in: global.settings.model_auto_unload_timeout_seconds=num:pos, self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
        branch br:075bba2b9a54 `not self._auto_unload_enabled() or self._backend is None or self._acti` = F
        call ModelManager._auto_unload_timeout  [returned]  state-in: global.settings.model_auto_unload_timeout_seconds=num:pos, self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
call ModelManager._cancel_idle_unload_timer  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=obj:Task, self._last_used_at=num:pos  Δ self._idle_unload_task: obj:Task→none
  branch br:be9c978e2166 `self._idle_unload_task and (not self._idle_unload_task.done()) and (se` = T

### test_ensure_backend_serializes_concurrent_reloads  (not scored: concurrency)
call ModelManager.__init__  [returned]  state-in: —  Δ self._config: ∅→obj:ModelConfig; self._backend: ∅→none; self._device: ∅→none; self._lock: ∅→obj:Lock; self._active_requests: ∅→num:zero; self._last_used_at: ∅→none; self._idle_unload_task: ∅→none
call ModelManager.ensure_backend  [returned]  state-in: self._active_requests=num:zero, self._backend=none, self._idle_unload_task=none, self._last_used_at=none  Δ self._backend: none→obj:stand-in
  branch br:1f44d4f2492f `self._backend` = F
  branch br:2c6c7a26afe6 `not self._backend` = T
  call ModelManager._cancel_idle_unload_timer  [returned]  state-in: self._active_requests=num:zero, self._backend=none, self._idle_unload_task=none, self._last_used_at=none
    branch br:be9c978e2166 `self._idle_unload_task and (not self._idle_unload_task.done()) and (se` = F
  call ModelManager.initialize (stand-in, not executed)  [returned]
call ModelManager.ensure_backend  [returned]  state-in: self._active_requests=num:zero, self._backend=none, self._idle_unload_task=none, self._last_used_at=none  Δ self._backend: none→obj:stand-in
  branch br:1f44d4f2492f `self._backend` = F
call ModelManager.ensure_backend  [returned]  state-in: self._active_requests=num:zero, self._backend=none, self._idle_unload_task=none, self._last_used_at=none  Δ self._backend: none→obj:stand-in
  branch br:1f44d4f2492f `self._backend` = F
call ModelManager.ensure_backend  [returned]  state-in: self._active_requests=num:zero, self._backend=none, self._idle_unload_task=none, self._last_used_at=none  Δ self._backend: none→obj:stand-in
  branch br:1f44d4f2492f `self._backend` = F
call ModelManager.ensure_backend  [returned]  state-in: self._active_requests=num:zero, self._backend=none, self._idle_unload_task=none, self._last_used_at=none  Δ self._backend: none→obj:stand-in
  branch br:1f44d4f2492f `self._backend` = F
  call ModelManager.load_model (stand-in, not executed)  [returned]
  branch br:2c6c7a26afe6 `not self._backend` = F
  branch br:2c6c7a26afe6 `not self._backend` = F
  branch br:2c6c7a26afe6 `not self._backend` = F
  branch br:2c6c7a26afe6 `not self._backend` = F

### test_generate_skips_reinit_when_backend_set
call ModelManager.__init__  [returned]  state-in: —  Δ self._config: ∅→obj:ModelConfig; self._backend: ∅→none; self._device: ∅→none; self._lock: ∅→obj:Lock; self._active_requests: ∅→num:zero; self._last_used_at: ∅→none; self._idle_unload_task: ∅→none
call ModelManager.generate  [returned]  state-in: global.settings.default_volume_multiplier=num:pos, self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none  Δ self._last_used_at: none→num:pos
  call ModelManager.hold  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none  Δ self._last_used_at: none→num:pos
    call ModelManager._begin_request  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none  Δ self._active_requests: num:zero→num:pos
      call ModelManager._cancel_idle_unload_timer  [returned]  state-in: self._active_requests=num:pos, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none
        branch br:be9c978e2166 `self._idle_unload_task and (not self._idle_unload_task.done()) and (se` = F
  call ModelManager.ensure_backend  [returned]  state-in: self._active_requests=num:pos, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none
    branch br:1f44d4f2492f `self._backend` = T
  branch br:1ae6dab118b9 `settings.default_volume_multiplier != 1.0` = F
    call ModelManager._end_request  [returned]  state-in: self._active_requests=num:pos, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none  Δ self._active_requests: num:pos→num:zero; self._last_used_at: none→num:pos
      call ModelManager._schedule_idle_unload_timer_locked  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
        call ModelManager._cancel_idle_unload_timer  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
          branch br:be9c978e2166 `self._idle_unload_task and (not self._idle_unload_task.done()) and (se` = F
        call ModelManager._auto_unload_enabled  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
          call ModelManager._auto_unload_timeout  [returned]  state-in: global.settings.model_auto_unload_timeout_seconds=num:zero, self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
        branch br:075bba2b9a54 `not self._auto_unload_enabled() or self._backend is None or self._acti` = T

### test_idle_auto_unload_log_includes_configured_timeout
call ModelManager.__init__  [returned]  state-in: —  Δ self._config: ∅→obj:ModelConfig; self._backend: ∅→none; self._device: ∅→none; self._lock: ∅→obj:Lock; self._active_requests: ∅→num:zero; self._last_used_at: ∅→none; self._idle_unload_task: ∅→none
call ModelManager._idle_unload_after  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:zero  Δ self._backend: obj:stand-in→none; self._last_used_at: num:zero→num:pos
  call ModelManager._auto_unload_enabled  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:zero
    call ModelManager._auto_unload_timeout  [returned]  state-in: global.settings.model_auto_unload_timeout_seconds=num:pos, self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:zero
  branch br:79d02f610d4d `not self._auto_unload_enabled() or self._backend is None or self._acti` = F
  call ModelManager._auto_unload_timeout  [returned]  state-in: global.settings.model_auto_unload_timeout_seconds=num:pos, self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:zero
  branch br:bad1968a9b60 `idle_for < self._auto_unload_timeout()` = F
  call ModelManager._unload_backend_locked  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:zero  Δ self._backend: obj:stand-in→none; self._last_used_at: num:zero→num:pos
    branch br:e6f07b6d711d `self._backend is None` = F
  branch br:ed05503f84fe `unloaded` = T
  branch br:9eca4b37c953 `torch.cuda.is_available()` = F
  call ModelManager._auto_unload_timeout  [returned]  state-in: global.settings.model_auto_unload_timeout_seconds=num:pos, self._active_requests=num:zero, self._backend=none, self._idle_unload_task=none, self._last_used_at=num:pos
  call ModelManager._format_seconds  [returned]  state-in: self._active_requests=num:zero, self._backend=none, self._idle_unload_task=none, self._last_used_at=num:pos

### test_load_model_schedules_idle_unload_when_enabled
call ModelManager.__init__  [returned]  state-in: —  Δ self._config: ∅→obj:ModelConfig; self._backend: ∅→none; self._device: ∅→none; self._lock: ∅→obj:Lock; self._active_requests: ∅→num:zero; self._last_used_at: ∅→none; self._idle_unload_task: ∅→none
call ModelManager.load_model  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none  Δ self._last_used_at: none→num:pos; self._idle_unload_task: none→obj:Task
  branch br:34208645b556 `not self._backend` = F
  call ModelManager._schedule_idle_unload_timer_locked  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos  Δ self._idle_unload_task: none→obj:Task
    call ModelManager._cancel_idle_unload_timer  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
      branch br:be9c978e2166 `self._idle_unload_task and (not self._idle_unload_task.done()) and (se` = F
    call ModelManager._auto_unload_enabled  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
      call ModelManager._auto_unload_timeout  [returned]  state-in: global.settings.model_auto_unload_timeout_seconds=num:pos, self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
    branch br:075bba2b9a54 `not self._auto_unload_enabled() or self._backend is None or self._acti` = F
    call ModelManager._auto_unload_timeout  [returned]  state-in: global.settings.model_auto_unload_timeout_seconds=num:pos, self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
call ModelManager._idle_unload_after  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=obj:Task, self._last_used_at=num:pos  Δ self._backend: obj:stand-in→none
  call ModelManager._auto_unload_enabled  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=obj:Task, self._last_used_at=num:pos
    call ModelManager._auto_unload_timeout  [returned]  state-in: global.settings.model_auto_unload_timeout_seconds=num:pos, self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=obj:Task, self._last_used_at=num:pos
  branch br:79d02f610d4d `not self._auto_unload_enabled() or self._backend is None or self._acti` = F
  call ModelManager._auto_unload_timeout  [returned]  state-in: global.settings.model_auto_unload_timeout_seconds=num:pos, self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=obj:Task, self._last_used_at=num:pos
  branch br:bad1968a9b60 `idle_for < self._auto_unload_timeout()` = F
  call ModelManager._unload_backend_locked  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=obj:Task, self._last_used_at=num:pos  Δ self._backend: obj:stand-in→none
    branch br:e6f07b6d711d `self._backend is None` = F
  branch br:ed05503f84fe `unloaded` = T
  branch br:9eca4b37c953 `torch.cuda.is_available()` = F
  call ModelManager._auto_unload_timeout  [returned]  state-in: global.settings.model_auto_unload_timeout_seconds=num:pos, self._active_requests=num:zero, self._backend=none, self._idle_unload_task=obj:Task, self._last_used_at=num:pos
  call ModelManager._format_seconds  [returned]  state-in: self._active_requests=num:zero, self._backend=none, self._idle_unload_task=obj:Task, self._last_used_at=num:pos

### test_manager_init_creates_lock
call ModelManager.__init__  [returned]  state-in: —  Δ self._config: ∅→obj:ModelConfig; self._backend: ∅→none; self._device: ∅→none; self._lock: ∅→obj:Lock; self._active_requests: ∅→num:zero; self._last_used_at: ∅→none; self._idle_unload_task: ∅→none

### test_status_reports_model_lifecycle_state
call ModelManager.__init__  [returned]  state-in: —  Δ self._config: ∅→obj:ModelConfig; self._backend: ∅→none; self._device: ∅→none; self._lock: ∅→obj:Lock; self._active_requests: ∅→num:zero; self._last_used_at: ∅→none; self._idle_unload_task: ∅→none
call ModelManager.status  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
  call ModelManager._auto_unload_timeout  [returned]  state-in: global.settings.model_auto_unload_timeout_seconds=num:pos, self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
  branch br:a08083f9aeea `self._last_used_at is not None` = T
  call ModelManager._auto_unload_enabled  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
    call ModelManager._auto_unload_timeout  [returned]  state-in: global.settings.model_auto_unload_timeout_seconds=num:pos, self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
  branch br:cfda31c8127c `self._auto_unload_enabled() and self._backend is not None` = T
  call ModelManager.current_backend  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
  call ModelManager._auto_unload_enabled  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos
    call ModelManager._auto_unload_timeout  [returned]  state-in: global.settings.model_auto_unload_timeout_seconds=num:pos, self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=num:pos

### test_unload_calls_cuda_empty_cache_when_available
call ModelManager.__init__  [returned]  state-in: —  Δ self._config: ∅→obj:ModelConfig; self._backend: ∅→none; self._device: ∅→none; self._lock: ∅→obj:Lock; self._active_requests: ∅→num:zero; self._last_used_at: ∅→none; self._idle_unload_task: ∅→none
call ModelManager.unload  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none  Δ self._backend: obj:stand-in→none; self._last_used_at: none→num:pos
  call ModelManager._cancel_idle_unload_timer  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none
    branch br:be9c978e2166 `self._idle_unload_task and (not self._idle_unload_task.done()) and (se` = F
  call ModelManager._unload_backend_locked  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none  Δ self._backend: obj:stand-in→none; self._last_used_at: none→num:pos
    branch br:e6f07b6d711d `self._backend is None` = F
  branch br:4e5a06d4451e `torch.cuda.is_available()` = T

### test_unload_clears_backend
call ModelManager.__init__  [returned]  state-in: —  Δ self._config: ∅→obj:ModelConfig; self._backend: ∅→none; self._device: ∅→none; self._lock: ∅→obj:Lock; self._active_requests: ∅→num:zero; self._last_used_at: ∅→none; self._idle_unload_task: ∅→none
call ModelManager.unload  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none  Δ self._backend: obj:stand-in→none; self._last_used_at: none→num:pos
  call ModelManager._cancel_idle_unload_timer  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none
    branch br:be9c978e2166 `self._idle_unload_task and (not self._idle_unload_task.done()) and (se` = F
  call ModelManager._unload_backend_locked  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none  Δ self._backend: obj:stand-in→none; self._last_used_at: none→num:pos
    branch br:e6f07b6d711d `self._backend is None` = F
  branch br:4e5a06d4451e `torch.cuda.is_available()` = F

### test_unload_skips_cuda_empty_cache_when_unavailable
call ModelManager.__init__  [returned]  state-in: —  Δ self._config: ∅→obj:ModelConfig; self._backend: ∅→none; self._device: ∅→none; self._lock: ∅→obj:Lock; self._active_requests: ∅→num:zero; self._last_used_at: ∅→none; self._idle_unload_task: ∅→none
call ModelManager.unload  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none  Δ self._backend: obj:stand-in→none; self._last_used_at: none→num:pos
  call ModelManager._cancel_idle_unload_timer  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none
    branch br:be9c978e2166 `self._idle_unload_task and (not self._idle_unload_task.done()) and (se` = F
  call ModelManager._unload_backend_locked  [returned]  state-in: self._active_requests=num:zero, self._backend=obj:stand-in, self._idle_unload_task=none, self._last_used_at=none  Δ self._backend: obj:stand-in→none; self._last_used_at: none→num:pos
    branch br:e6f07b6d711d `self._backend is None` = F
  branch br:4e5a06d4451e `torch.cuda.is_available()` = F
```

Withheld (observed, not shown): test_generate_lazy_reinit_when_backend_none, test_generate_schedules_idle_unload_when_enabled, test_load_model_does_not_schedule_idle_unload_during_active_request, test_unload_when_already_none_is_noop

## Source: api/src/inference/model_manager.py

```python
   1  """Kokoro V1 model management."""
   2  
   3  import asyncio
   4  import time
   5  from contextlib import asynccontextmanager
   6  from typing import Optional
   7  
   8  import torch
   9  from loguru import logger
  10  
  11  from ..core import paths
  12  from ..core.config import settings
  13  from ..core.model_config import ModelConfig, model_config
  14  from .base import BaseModelBackend
  15  from .kokoro_v1 import KokoroV1
  16  
  17  
  18  class ModelManager:
  19      """Manages Kokoro V1 model loading and inference."""
  20  
  21      # Singleton instance
  22      _instance = None
  23  
  24      def __init__(self, config: Optional[ModelConfig] = None):
  25          """Initialize manager.
  26  
  27          Args:
  28              config: Optional model configuration override
  29          """
  30          self._config = config or model_config
  31          self._backend: Optional[KokoroV1] = None  # Explicitly type as KokoroV1
  32          self._device: Optional[str] = None
  33          self._lock = asyncio.Lock()
  34          self._active_requests = 0
  35          self._last_used_at: Optional[float] = None
  36          self._idle_unload_task: Optional[asyncio.Task] = None
  37  
  38      def _determine_device(self) -> str:
  39          """Determine device based on settings."""
  40          return "cuda" if settings.use_gpu else "cpu"
  41  
  42      async def initialize(self) -> None:
  43          """Initialize Kokoro V1 backend."""
  44          try:
  45              self._device = self._determine_device()
  46              logger.info(f"Initializing Kokoro V1 on {self._device}")
  47              self._backend = KokoroV1()
  48  
  49          except Exception as e:
  50              raise RuntimeError(f"Failed to initialize Kokoro V1: {e}")
  51  
  52      async def initialize_with_warmup(self, voice_manager) -> tuple[str, str, int]:
  53          """Initialize and warm up model.
  54  
  55          Args:
  56              voice_manager: Voice manager instance for warmup
  57  
  58          Returns:
  59              Tuple of (device, backend type, voice count)
  60  
  61          Raises:
  62              RuntimeError: If initialization fails
  63          """
  64          import time
  65  
  66          start = time.perf_counter()
  67  
  68          try:
  69              # Initialize backend
  70              await self.initialize()
  71  
  72              # Load model
  73              model_path = self._config.pytorch_kokoro_v1_file
  74              await self.load_model(model_path)
  75  
  76              # Use paths module to get voice path
  77              try:
  78                  voices = await paths.list_voices()
  79                  voice_path = await paths.get_voice_path(settings.default_voice)
  80  
  81                  # Warm up with short text
  82                  warmup_text = "Warmup text for initialization."
  83                  # Use default voice name for warmup
  84                  voice_name = settings.default_voice
  85                  logger.debug(f"Using default voice '{voice_name}' for warmup")
  86                  async for _ in self.generate(warmup_text, (voice_name, voice_path)):
  87                      pass
  88              except Exception as e:
  89                  raise RuntimeError(f"Failed to get default voice: {e}")
  90  
  91              ms = int((time.perf_counter() - start) * 1000)
  92              logger.info(f"Warmup completed in {ms}ms")
  93  
  94              return self._device, "kokoro_v1", len(voices)
  95          except FileNotFoundError as e:
  96              logger.error("""
  97  Model files not found! You need to download the Kokoro V1 model:
  98  
  99  1. Download model using the script:
 100     python docker/scripts/download_model.py --output api/src/models/v1_0
 101  
 102  2. Or set environment variable in docker-compose:
 103     DOWNLOAD_MODEL=true
 104  """)
 105              exit(0)
 106          except Exception as e:
 107              raise RuntimeError(f"Warmup failed: {e}")
 108  
 109      async def ensure_backend(self) -> None:
 110          """Reload the backend if it was unloaded."""
 111          if self._backend:
 112              return
 113          async with self._lock:
 114              if not self._backend:
 115                  self._cancel_idle_unload_timer()
 116                  await self.initialize()
 117                  await self.load_model(self._config.pytorch_kokoro_v1_file)
 118  
 119      def get_backend(self) -> BaseModelBackend:
 120          """Get initialized backend.
 121  
 122          Returns:
 123              Initialized backend instance
 124  
 125          Raises:
 126              RuntimeError: If backend not initialized
 127          """
 128          if not self._backend:
 129              raise RuntimeError("Backend not initialized")
 130          return self._backend
 131  
 132      async def load_model(self, path: str) -> None:
 133          """Load model using initialized backend.
 134  
 135          Args:
 136              path: Path to model file
 137  
 138          Raises:
 139              RuntimeError: If loading fails
 140          """
 141          if not self._backend:
 142              raise RuntimeError("Backend not initialized")
 143  
 144          try:
 145              await self._backend.load_model(path)
 146              self._last_used_at = time.monotonic()
 147              self._schedule_idle_unload_timer_locked()
 148          except FileNotFoundError as e:
 149              raise e
 150          except Exception as e:
 151              raise RuntimeError(f"Failed to load model: {e}")
 152  
 153      def _auto_unload_timeout(self) -> float:
 154          return max(0.0, float(settings.model_auto_unload_timeout_seconds))
 155  
 156      def _format_seconds(self, seconds: float) -> str:
 157          return f"{seconds:g}s"
 158  
 159      def _auto_unload_enabled(self) -> bool:
 160          return self._auto_unload_timeout() > 0
 161  
 162      def _cancel_idle_unload_timer(self) -> None:
 163          try:
 164              current_task = asyncio.current_task()
 165          except RuntimeError:
 166              current_task = None
 167          if (
 168              self._idle_unload_task
 169              and not self._idle_unload_task.done()
 170              and self._idle_unload_task is not current_task
 171          ):
 172              self._idle_unload_task.cancel()
 173          self._idle_unload_task = None
 174  
 175      def _unload_backend_locked(self) -> bool:
 176          if self._backend is None:
 177              return False
 178          self._backend.unload()
 179          self._backend = None
 180          self._last_used_at = time.monotonic()
 181          return True
 182  
 183      def _schedule_idle_unload_timer_locked(self) -> None:
 184          self._cancel_idle_unload_timer()
 185          if (
 186              not self._auto_unload_enabled()
 187              or self._backend is None
 188              or self._active_requests > 0
 189          ):
 190              return
 191  
 192          timeout = self._auto_unload_timeout()
 193          self._idle_unload_task = asyncio.create_task(self._idle_unload_after(timeout))
 194  
 195      async def _idle_unload_after(self, timeout: float) -> None:
 196          try:
 197              await asyncio.sleep(timeout)
 198              async with self._lock:
 199                  if (
 200                      not self._auto_unload_enabled()
 201                      or self._backend is None
 202                      or self._active_requests > 0
 203                      or self._last_used_at is None
 204                  ):
 205                      return
 206  
 207                  idle_for = time.monotonic() - self._last_used_at
 208                  if idle_for < self._auto_unload_timeout():
 209                      self._schedule_idle_unload_timer_locked()
 210                      return
 211  
 212                  unloaded = self._unload_backend_locked()
 213  
 214              if unloaded:
 215                  if torch.cuda.is_available():
 216                      torch.cuda.empty_cache()
 217                  logger.info(
 218                      "Model auto-unloaded after idle timeout of "
 219                      f"{self._format_seconds(self._auto_unload_timeout())}"
 220                  )
 221          except asyncio.CancelledError:
 222              pass
 223  
 224      async def _begin_request(self) -> None:
 225          async with self._lock:
 226              self._active_requests += 1
 227              self._cancel_idle_unload_timer()
 228  
 229      async def _end_request(self) -> None:
 230          async with self._lock:
 231              self._active_requests = max(0, self._active_requests - 1)
 232              self._last_used_at = time.monotonic()
 233              self._schedule_idle_unload_timer_locked()
 234  
 235      @asynccontextmanager
 236      async def hold(self):
 237          await self._begin_request()
 238          try:
 239              yield
 240          finally:
 241              await self._end_request()
 242  
 243      async def generate(self, *args, **kwargs):
 244          """Generate audio using initialized backend.
 245  
 246          Raises:
 247              RuntimeError: If generation fails
 248          """
 249          try:
 250              async with self.hold():
 251                  await self.ensure_backend()
 252                  assert self._backend is not None, "ensure_backend left no backend"
 253                  async for chunk in self._backend.generate(*args, **kwargs):
 254                      if settings.default_volume_multiplier != 1.0:
 255                          chunk.audio *= settings.default_volume_multiplier
 256                      yield chunk
 257          except Exception as e:
 258              raise RuntimeError(f"Generation failed: {e}")
 259  
 260      def unload_all(self) -> None:
 261          """Unload model and free resources."""
 262          self._cancel_idle_unload_timer()
 263          if self._backend:
 264              self._backend.unload()
 265              self._backend = None
 266  
 267      async def unload(self) -> None:
 268          """Release model from GPU memory. Reloads automatically on next request."""
 269          async with self._lock:
 270              self._cancel_idle_unload_timer()
 271              self._unload_backend_locked()
 272          if torch.cuda.is_available():
 273              torch.cuda.empty_cache()
 274          logger.info("Model unloaded from GPU memory")
 275  
 276      async def reload(self) -> None:
 277          """Reload the model immediately."""
 278          async with self._lock:
 279              self._cancel_idle_unload_timer()
 280              self._unload_backend_locked()
 281              await self.initialize()
 282              await self.load_model(self._config.pytorch_kokoro_v1_file)
 283              self._schedule_idle_unload_timer_locked()
 284          logger.info("Model reloaded")
 285  
 286      def status(self) -> dict:
 287          """Return model lifecycle state for API responses."""
 288          timeout = self._auto_unload_timeout()
 289          idle_for = None
 290          unload_in = None
 291          if self._last_used_at is not None:
 292              idle_for = max(0.0, time.monotonic() - self._last_used_at)
 293              if self._auto_unload_enabled() and self._backend is not None:
 294                  unload_in = max(0.0, timeout - idle_for)
 295          return {
 296              "backend": self.current_backend,
 297              "device": self._device,
 298              "loaded": self._backend is not None,
 299              "active_requests": self._active_requests,
 300              "auto_unload_enabled": self._auto_unload_enabled(),
 301              "auto_unload_timeout_seconds": timeout,
 302              "idle_seconds": idle_for,
 303              "seconds_until_auto_unload": unload_in,
 304          }
 305  
 306      @property
 307      def current_backend(self) -> str:
 308          """Get current backend type."""
 309          return "kokoro_v1"
 310  
 311  
 312  async def get_manager(config: Optional[ModelConfig] = None) -> ModelManager:
 313      """Get model manager instance.
 314  
 315      Args:
 316          config: Optional configuration override
 317  
 318      Returns:
 319          ModelManager instance
 320      """
 321      if ModelManager._instance is None:
 322          ModelManager._instance = ModelManager(config)
 323      return ModelManager._instance
```

## Source: api/tests/test_model_unload.py (lines 1-311)

```python
   1  """Tests for model unload, auto-unload, lazy reload, and dev lifecycle endpoints."""
   2  
   3  import asyncio
   4  from contextlib import contextmanager
   5  from unittest.mock import AsyncMock, MagicMock, patch
   6  
   7  import numpy as np
   8  import pytest
   9  from fastapi.testclient import TestClient
  10  
  11  from api.src.core.config import settings
  12  from api.src.inference.base import AudioChunk
  13  from api.src.inference.model_manager import ModelManager
  14  from api.src.main import app
  15  from api.src.routers.development import get_tts_service
  16  from api.src.services.tts_service import TTSService
  17  
  18  client = TestClient(app)
  19  
  20  
  21  @contextmanager
  22  def override_tts_service(service):
  23      """Override the get_tts_service FastAPI dependency for the duration of the block."""
  24  
  25      async def _override():
  26          return service
  27  
  28      app.dependency_overrides[get_tts_service] = _override
  29      try:
  30          yield
  31      finally:
  32          app.dependency_overrides.pop(get_tts_service, None)
  33  
  34  
  35  @pytest.fixture(autouse=True)
  36  def _enable_dev_unload(monkeypatch):
  37      """Enable the /dev/unload gate for the endpoint tests in this module."""
  38      monkeypatch.setattr(settings, "allow_dev_unload", True)
  39      monkeypatch.setattr(settings, "model_auto_unload_timeout_seconds", 0.0)
  40  
  41  
  42  # ---------------------------------------------------------------------------
  43  # ModelManager unit tests
  44  # ---------------------------------------------------------------------------
  45  
  46  
  47  def test_manager_init_creates_lock():
  48      manager = ModelManager()
  49      assert isinstance(manager._lock, asyncio.Lock)
  50      assert manager._active_requests == 0
  51  
  52  
  53  @pytest.mark.asyncio
  54  async def test_unload_clears_backend():
  55      manager = ModelManager()
  56      mock_backend = MagicMock()
  57      manager._backend = mock_backend
  58  
  59      with patch("api.src.inference.model_manager.torch") as mock_torch:
  60          mock_torch.cuda.is_available.return_value = False
  61          await manager.unload()
  62  
  63      mock_backend.unload.assert_called_once()
  64      assert manager._backend is None
  65  
  66  
  67  @pytest.mark.asyncio
  68  async def test_unload_when_already_none_is_noop():
  69      manager = ModelManager()
  70      assert manager._backend is None
  71  
  72      with patch("api.src.inference.model_manager.torch") as mock_torch:
  73          mock_torch.cuda.is_available.return_value = False
  74          await manager.unload()  # must not raise
  75  
  76      assert manager._backend is None
  77  
  78  
  79  @pytest.mark.asyncio
  80  async def test_unload_calls_cuda_empty_cache_when_available():
  81      manager = ModelManager()
  82      manager._backend = MagicMock()
  83  
  84      with patch("api.src.inference.model_manager.torch") as mock_torch:
  85          mock_torch.cuda.is_available.return_value = True
  86          await manager.unload()
  87  
  88      mock_torch.cuda.empty_cache.assert_called_once()
  89  
  90  
  91  @pytest.mark.asyncio
  92  async def test_unload_skips_cuda_empty_cache_when_unavailable():
  93      manager = ModelManager()
  94      manager._backend = MagicMock()
  95  
  96      with patch("api.src.inference.model_manager.torch") as mock_torch:
  97          mock_torch.cuda.is_available.return_value = False
  98          await manager.unload()
  99  
 100      mock_torch.cuda.empty_cache.assert_not_called()
 101  
 102  
 103  @pytest.mark.asyncio
 104  async def test_ensure_backend_serializes_concurrent_reloads():
 105      """Concurrent callers when _backend is None should trigger only one load cycle."""
 106      manager = ModelManager()
 107      assert manager._backend is None
 108  
 109      mock_backend = MagicMock()
 110      init_count = 0
 111      load_count = 0
 112  
 113      async def fake_initialize():
 114          nonlocal init_count
 115          init_count += 1
 116          await asyncio.sleep(0)  # yield so other tasks can attempt entry
 117          manager._backend = mock_backend
 118  
 119      async def fake_load(path):
 120          nonlocal load_count
 121          load_count += 1
 122  
 123      with (
 124          patch.object(manager, "initialize", side_effect=fake_initialize),
 125          patch.object(manager, "load_model", side_effect=fake_load),
 126      ):
 127          await asyncio.gather(*[manager.ensure_backend() for _ in range(5)])
 128  
 129      assert init_count == 1
 130      assert load_count == 1
 131  
 132  
 133  @pytest.mark.asyncio
 134  async def test_generate_lazy_reinit_when_backend_none():
 135      """generate() initializes backend lazily when _backend is None."""
 136      manager = ModelManager()
 137      assert manager._backend is None
 138  
 139      mock_backend = MagicMock()
 140      audio_chunk = AudioChunk(np.zeros(10, dtype=np.float32))
 141  
 142      async def fake_generate(*args, **kwargs):
 143          yield audio_chunk
 144  
 145      mock_backend.generate = fake_generate
 146  
 147      async def fake_initialize():
 148          manager._backend = mock_backend
 149  
 150      with (
 151          patch.object(manager, "initialize", side_effect=fake_initialize) as mock_init,
 152          patch.object(manager, "load_model", new_callable=AsyncMock) as mock_load,
 153      ):
 154          chunks = []
 155          async for chunk in manager.generate("hello", ("voice", "/path/voice.pt")):
 156              chunks.append(chunk)
 157  
 158      mock_init.assert_called_once()
 159      mock_load.assert_called_once_with(manager._config.pytorch_kokoro_v1_file)
 160      assert len(chunks) == 1
 161      assert chunks[0] is audio_chunk
 162  
 163  
 164  @pytest.mark.asyncio
 165  async def test_generate_skips_reinit_when_backend_set():
 166      """generate() does not call initialize/load_model when backend already exists."""
 167      manager = ModelManager()
 168      mock_backend = MagicMock()
 169      audio_chunk = AudioChunk(np.zeros(10, dtype=np.float32))
 170  
 171      async def fake_generate(*args, **kwargs):
 172          yield audio_chunk
 173  
 174      mock_backend.generate = fake_generate
 175      manager._backend = mock_backend
 176  
 177      with (
 178          patch.object(manager, "initialize", new_callable=AsyncMock) as mock_init,
 179          patch.object(manager, "load_model", new_callable=AsyncMock) as mock_load,
 180      ):
 181          chunks = []
 182          async for chunk in manager.generate("hello", ("voice", "/path/voice.pt")):
 183              chunks.append(chunk)
 184  
 185      mock_init.assert_not_called()
 186      mock_load.assert_not_called()
 187      assert len(chunks) == 1
 188  
 189  
 190  @pytest.mark.asyncio
 191  async def test_generate_schedules_idle_unload_when_enabled(monkeypatch):
 192      """Finished generation schedules model unload after the configured idle period."""
 193      monkeypatch.setattr(settings, "model_auto_unload_timeout_seconds", 0.01)
 194  
 195      manager = ModelManager()
 196      mock_backend = MagicMock()
 197      audio_chunk = AudioChunk(np.zeros(10, dtype=np.float32))
 198  
 199      async def fake_generate(*args, **kwargs):
 200          yield audio_chunk
 201  
 202      mock_backend.generate = fake_generate
 203      manager._backend = mock_backend
 204  
 205      with patch("api.src.inference.model_manager.torch") as mock_torch:
 206          mock_torch.cuda.is_available.return_value = False
 207          chunks = []
 208          async for chunk in manager.generate("hello", ("voice", "/path/voice.pt")):
 209              chunks.append(chunk)
 210          await asyncio.sleep(0.03)
 211  
 212      assert len(chunks) == 1
 213      mock_backend.unload.assert_called_once()
 214      assert manager._backend is None
 215  
 216  
 217  @pytest.mark.asyncio
 218  async def test_idle_auto_unload_log_includes_configured_timeout(monkeypatch):
 219      monkeypatch.setattr(settings, "model_auto_unload_timeout_seconds", 30.0)
 220  
 221      manager = ModelManager()
 222      mock_backend = MagicMock()
 223      manager._backend = mock_backend
 224      manager._last_used_at = 0.0
 225  
 226      with (
 227          patch("api.src.inference.model_manager.time.monotonic", return_value=31.0),
 228          patch("api.src.inference.model_manager.torch") as mock_torch,
 229          patch("api.src.inference.model_manager.logger.info") as mock_log_info,
 230      ):
 231          mock_torch.cuda.is_available.return_value = False
 232          await manager._idle_unload_after(0)
 233  
 234      mock_backend.unload.assert_called_once()
 235      mock_log_info.assert_any_call("Model auto-unloaded after idle timeout of 30s")
 236  
 237  
 238  @pytest.mark.asyncio
 239  async def test_load_model_schedules_idle_unload_when_enabled(monkeypatch):
 240      """Startup-style model loads also schedule unload without waiting for traffic."""
 241      monkeypatch.setattr(settings, "model_auto_unload_timeout_seconds", 0.01)
 242  
 243      manager = ModelManager()
 244      mock_backend = MagicMock()
 245      mock_backend.load_model = AsyncMock()
 246      manager._backend = mock_backend
 247  
 248      with patch("api.src.inference.model_manager.torch") as mock_torch:
 249          mock_torch.cuda.is_available.return_value = False
 250          await manager.load_model("/path/model.pt")
 251          await asyncio.sleep(0.03)
 252  
 253      mock_backend.load_model.assert_called_once_with("/path/model.pt")
 254      mock_backend.unload.assert_called_once()
 255      assert manager._backend is None
 256  
 257  
 258  @pytest.mark.asyncio
 259  async def test_load_model_does_not_schedule_idle_unload_during_active_request(
 260      monkeypatch,
 261  ):
 262      """Lazy loads during generation wait for request completion before scheduling."""
 263      monkeypatch.setattr(settings, "model_auto_unload_timeout_seconds", 0.01)
 264  
 265      manager = ModelManager()
 266      mock_backend = MagicMock()
 267      mock_backend.load_model = AsyncMock()
 268      manager._backend = mock_backend
 269      manager._active_requests = 1
 270  
 271      await manager.load_model("/path/model.pt")
 272      await asyncio.sleep(0.03)
 273  
 274      mock_backend.load_model.assert_called_once_with("/path/model.pt")
 275      mock_backend.unload.assert_not_called()
 276      assert manager._backend is mock_backend
 277      assert manager._idle_unload_task is None
 278  
 279  
 280  @pytest.mark.asyncio
 281  async def test_active_request_blocks_idle_unload(monkeypatch):
 282      """The idle timer does not unload while generation is still active."""
 283      monkeypatch.setattr(settings, "model_auto_unload_timeout_seconds", 0.01)
 284  
 285      manager = ModelManager()
 286      mock_backend = MagicMock()
 287  
 288      async def slow_generate(*args, **kwargs):
 289          await asyncio.sleep(0.03)
 290          yield AudioChunk(np.zeros(10, dtype=np.float32))
 291  
 292      mock_backend.generate = slow_generate
 293      manager._backend = mock_backend
 294  
 295      with patch("api.src.inference.model_manager.torch") as mock_torch:
 296          mock_torch.cuda.is_available.return_value = False
 297          chunks = []
 298          async for chunk in manager.generate("hello", ("voice", "/path/voice.pt")):
 299              assert manager._active_requests == 1
 300              mock_backend.unload.assert_not_called()
 301              chunks.append(chunk)
 302  
 303      assert len(chunks) == 1
 304      assert manager._active_requests == 0
 305      assert manager._idle_unload_task is not None
 306      manager._cancel_idle_unload_timer()
 307  
 308  
 309  def test_status_reports_model_lifecycle_state(monkeypatch):
 310      monkeypatch.setattr(settings, "model_auto_unload_timeout_seconds", 30.0)
 311      manager = ModelManager()
```
