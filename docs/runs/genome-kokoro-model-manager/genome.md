# Behavioral Genome — Kokoro-FastAPI ModelManager lifecycle (`diffgenome-genome/0`, experimental)

Entry `ModelManager`. Semantic items proposed by `claude-opus-5-5` from a bounded context bundle (sha `3a1ae9e7a4b03316`); every status below was assigned by the deterministic checker, not by the model. Statuses: observed · static · HYPOTHESIS · supported (all citations check out) · VERIFIED (cites an `if` site and both branches observed, no contradiction) · REJECTED (contradicted by an execution).

## Entities (collector facts)


## Variables

- `backend_loaded` (state) ↔ observed `self._backend` (is_set) — supported
- `active_requests` (state) ↔ observed `self._active_requests` (sign) — supported
- `last_used_set` (state) ↔ observed `self._last_used_at` (is_set) — supported
- `timer_pending` (state) ↔ observed `self._idle_unload_task` (is_set) — supported
- `unload_timeout` (setting) ↔ observed `global.settings.model_auto_unload_timeout_seconds` (sign) — supported
- `idle_expired` (input) — supported
- `cuda_available` (input) — supported
- `volume_scaled` (setting) — supported
- `unloaded` (derived) — supported

## Data dependencies


## Decisions, in path order

### d_eb_fast · `backend_loaded` at `ModelManager.ensure_backend` site `br:1f44d4f2492f` — VERIFIED

- TRUE : (no call); never self._cancel_idle_unload_timer, self.initialize, self.load_model; **stop** — fast path: backend present, nothing to do
- FALSE: (no call); continue — take the lock and re-check
- status: site br:1f44d4f2492f (`self._backend`) observed true in 2 and false in 1 execution(s); the predicate agrees with the observed outcome 2 time(s) from observed state and in 2 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ source api/src/inference/model_manager.py:111 `if self._backend:`
  - ✓ branch None → None
  - ✓ branch None → None

### d_get_backend · `!backend_loaded` at `ModelManager.get_backend` site `br:5ea6e7329f80` — supported

- TRUE : (no call); **stop** — raise RuntimeError('Backend not initialized')
- FALSE: (no call); continue — return backend
- status: every cited reference checks out (control, source); site: br:5ea6e7329f80 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source api/src/inference/model_manager.py:128 `if not self._backend:`
  - ✓ control None → RuntimeError

### d_load_guard · `!backend_loaded` at `ModelManager.load_model` site `br:34208645b556` — supported

- TRUE : (no call); never self._backend.load_model, self._schedule_idle_unload_timer_locked; **stop** — raise RuntimeError('Backend not initialized')
- FALSE: (no call); continue — load weights, stamp last_used, schedule idle timer
- status: every cited reference checks out (branch, control, source); site: br:34208645b556 (given); not verified: outcome true never observed at br:34208645b556
  - ✓ source api/src/inference/model_manager.py:141 `if not self._backend:`
  - ✓ branch None → None
  - ✓ control None → self._schedule_idle_unload_timer_locked

### d_cancel · `timer_pending` at `ModelManager._cancel_idle_unload_timer` site `br:be9c978e2166` — VERIFIED

- TRUE : self._idle_unload_task.cancel; continue — cancel the live timer task (abstraction: a stored task is assumed not done and not the current task)
- FALSE: (no call); never self._idle_unload_task.cancel; continue — nothing to cancel
- status: site br:be9c978e2166 (`self._idle_unload_task and (not self._idle_unload_task.done()) and (self._idle_unload_task is not current_task)`) observed true in 1 and false in 7 execution(s); the predicate agrees with the observed outcome 9 time(s) from observed state and in 6 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ source api/src/inference/model_manager.py:169 `and not self._idle_unload_task.done()`
  - ✓ source api/src/inference/model_manager.py:170 `and self._idle_unload_task is not current_task`
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ control None → self._idle_unload_task.cancel

### d_unload_guard · `!backend_loaded` at `ModelManager._unload_backend_locked` site `br:e6f07b6d711d` — supported

- TRUE : (no call); never self._backend.unload; **stop** — no backend: return False, state untouched
- FALSE: self._backend.unload; continue — release backend, stamp last_used, return True
- status: every cited reference checks out (branch, control, source); site: br:e6f07b6d711d (given); not verified: outcome true never observed at br:e6f07b6d711d
  - ✓ source api/src/inference/model_manager.py:176 `if self._backend is None:`
  - ✓ branch None → None
  - ✓ control None → self._backend.unload

### d_schedule · `unload_timeout <= 0 || !backend_loaded || active_requests > 0` at `ModelManager._schedule_idle_unload_timer_locked` site `br:075bba2b9a54` — VERIFIED

- TRUE : (no call); never asyncio.create_task; **stop** — do not arm: auto-unload disabled, nothing loaded, or a request is in flight (timer stays cleared by the preceding cancel)
- FALSE: self._auto_unload_timeout → asyncio.create_task; continue — arm a new idle-unload task
- status: site br:075bba2b9a54 (`not self._auto_unload_enabled() or self._backend is None or self._active_requests > 0`) observed true in 1 and false in 2 execution(s); the predicate agrees with the observed outcome 3 time(s) from observed state and in 3 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ source api/src/inference/model_manager.py:186 `not self._auto_unload_enabled()`
  - ✓ source api/src/inference/model_manager.py:187 `or self._backend is None`
  - ✓ source api/src/inference/model_manager.py:188 `or self._active_requests > 0`
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ control None → asyncio.create_task

### d_idle_guard · `unload_timeout <= 0 || !backend_loaded || active_requests > 0 || !last_used_set` at `ModelManager._idle_unload_after` site `br:79d02f610d4d` — supported

- TRUE : (no call); never self._unload_backend_locked; **stop** — timer fired but unloading is not appropriate: exit silently
- FALSE: time.monotonic; continue — measure idle time
- status: every cited reference checks out (branch, source); site: br:79d02f610d4d (given); not verified: outcome true never observed at br:79d02f610d4d
  - ✓ source api/src/inference/model_manager.py:203 `or self._last_used_at is None`
  - ✓ branch None → None
  - ✓ branch None → None

### d_volume · `volume_scaled` at `ModelManager.generate` site `br:1ae6dab118b9` — supported

- TRUE : (no call); continue — scale chunk.audio by the multiplier (per chunk)
- FALSE: (no call); continue — yield chunk unchanged
- status: every cited reference checks out (branch, source); site: br:1ae6dab118b9 (given); not verified: outcome true never observed at br:1ae6dab118b9
  - ✓ source api/src/inference/model_manager.py:254 `if settings.default_volume_multiplier != 1.0:`
  - ✓ branch None → None

### d_unload_all · `backend_loaded` at `ModelManager.unload_all` site `br:60ebe4954dd3` — supported

- TRUE : self._backend.unload; continue — release backend (last_used untouched)
- FALSE: (no call); never self._backend.unload; continue — nothing loaded
- status: every cited reference checks out (source); site: br:60ebe4954dd3 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source api/src/inference/model_manager.py:263 `if self._backend:`
  - ✓ source api/src/inference/model_manager.py:265 `self._backend = None`

### d_unload_cuda · `cuda_available` at `ModelManager.unload` site `br:4e5a06d4451e` — VERIFIED

- TRUE : torch.cuda.empty_cache; continue — free GPU cache
- FALSE: (no call); never torch.cuda.empty_cache; continue — skip cache flush
- status: site br:4e5a06d4451e (`torch.cuda.is_available()`) observed true in 1 and false in 2 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 3 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ source api/src/inference/model_manager.py:272 `if torch.cuda.is_available():`
  - ✓ branch None → None
  - ✓ branch None → None

### d_status_last · `last_used_set` at `ModelManager.status` site `br:a08083f9aeea` — supported

- TRUE : time.monotonic; continue — report idle_seconds
- FALSE: (no call); continue — idle_seconds and seconds_until_auto_unload are None
- status: every cited reference checks out (branch, source); site: br:a08083f9aeea (given); not verified: outcome false never observed at br:a08083f9aeea
  - ✓ source api/src/inference/model_manager.py:291 `if self._last_used_at is not None:`
  - ✓ branch None → None

### d_eb_locked · `!backend_loaded` at `ModelManager.ensure_backend` site `br:2c6c7a26afe6` — supported

- TRUE : ModelManager._cancel_idle_unload_timer → ModelManager.initialize → ModelManager.load_model; continue — lazy re-init: cancel timer, initialize (backend becomes set), then load_model. load_model is omitted from steps because every test reaching this path stubs it (see unknowns).
- FALSE: (no call); never self.initialize, self.load_model; continue — another caller already reloaded while we waited for the lock
- status: every cited reference checks out (branch, control, delta, source); site: br:2c6c7a26afe6 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source api/src/inference/model_manager.py:114 `if not self._backend:`
  - ✓ branch None → None
  - ✓ control None → self.initialize
  - ✓ control None → self.load_model
  - ✓ delta None → None

### d_idle_recent · `!idle_expired` at `ModelManager._idle_unload_after` site `br:bad1968a9b60` — supported

- TRUE : (no call); never self._unload_backend_locked; **stop** — used again recently: re-arm the timer and exit
- FALSE: (no call); continue — idle long enough: unload
- status: every cited reference checks out (branch, control, source); site: br:bad1968a9b60 (given); not verified: outcome true never observed at br:bad1968a9b60
  - ✓ source api/src/inference/model_manager.py:208 `if idle_for < self._auto_unload_timeout():`
  - ✓ branch None → None
  - ✓ control None → self._schedule_idle_unload_timer_locked

### d_status_unload_in · `unload_timeout > 0 && backend_loaded` at `ModelManager.status` site `br:cfda31c8127c` — supported

- TRUE : (no call); continue — report seconds_until_auto_unload = max(0, timeout - idle)
- FALSE: (no call); continue — seconds_until_auto_unload is None
- status: every cited reference checks out (branch, source); site: br:cfda31c8127c (given); not verified: outcome false never observed at br:cfda31c8127c
  - ✓ source api/src/inference/model_manager.py:293 `if self._auto_unload_enabled() and self._backend is not None:`
  - ✓ branch None → None

### d_idle_unloaded · `unloaded` at `ModelManager._idle_unload_after` site `br:ed05503f84fe` — supported

- TRUE : (no call); continue — empty CUDA cache if available and log 'Model auto-unloaded after idle timeout of <timeout>'
- FALSE: (no call); never logger.info; continue — nothing was unloaded; no log
- status: every cited reference checks out (branch, control, source); site: br:ed05503f84fe (given); not verified: outcome false never observed at br:ed05503f84fe
  - ✓ source api/src/inference/model_manager.py:214 `if unloaded:`
  - ✓ branch None → None
  - ✓ control None → logger.info

### d_idle_cuda · `cuda_available` at `ModelManager._idle_unload_after` site `br:9eca4b37c953` — supported

- TRUE : torch.cuda.empty_cache; continue — free GPU cache
- FALSE: (no call); never torch.cuda.empty_cache; continue — skip cache flush
- status: every cited reference checks out (branch, source); site: br:9eca4b37c953 (given); not verified: outcome true never observed at br:9eca4b37c953
  - ✓ source api/src/inference/model_manager.py:215 `if torch.cuda.is_available():`
  - ✓ branch None → None

## Behavioral rules

- **r_timer_arming Idle timer is armed only when quiescent** — supported
  - when `unload_timeout > 0 && backend_loaded && active_requests == 0`
  - then Every schedule first cancels any existing timer (timer_pending=false); then arms a fresh timer (timer_pending=true) iff condition holds; schedule points: end of load_model, end of each request, end of reload, idle timer re-arm
  - summarizes d_schedule; every cited reference checks out (branch)
- **r_request_suspends_timer Active requests suspend auto-unload** — supported
  - when `a request begins`
  - then active_requests increments and the idle timer is cancelled; on request end active_requests decrements, last_used is stamped and the timer is rescheduled
- **r_idle_fire Timer firing unloads only a quiescent, genuinely idle backend** — supported
  - when `unload_timeout > 0 && backend_loaded && active_requests == 0 && last_used_set && idle_expired`
  - then backend released, last_used stamped, cache flushed if CUDA, log line with configured timeout; if not idle_expired the timer re-arms instead; timer handle stays set (done task) after a firing that unloads
  - summarizes d_idle_guard; every cited reference checks out (delta)
- **r_lazy_reload Backend is lazily re-created on demand** — supported
  - when `!backend_loaded when ensure_backend runs (double-checked under the lock)`
  - then cancel timer, initialize (backend_loaded=true), load_model
  - summarizes d_eb_locked; every cited reference checks out (branch)
- **r_unload_idempotent Unload is idempotent** — supported
  - when `unload with backend_loaded == false`
  - then no state change (last_used not stamped), no error; CUDA cache still flushed if available
  - summarizes d_unload_guard; every cited reference checks out (source)

## Regimes (behavioral equivalence classes)

- **Auto-unload disabled (timeout 0, module fixture default)** — 8 test(s): test_generate_skips_reinit_when_backend_set, test_generate_lazy_reinit_when_backend_none, test_unload_clears_backend, test_unload_when_already_none_is_noop, test_unload_calls_cuda_empty_cache_when_available, test_unload_skips_cuda_empty_cache_when_unavailable, test_manager_init_creates_lock, test_ensure_backend_serializes_concurrent_reloads — supported
- **Auto-unload enabled (timeout > 0)** — 6 test(s): test_active_request_blocks_idle_unload, test_generate_schedules_idle_unload_when_enabled, test_idle_auto_unload_log_includes_configured_timeout, test_load_model_schedules_idle_unload_when_enabled, test_load_model_does_not_schedule_idle_unload_during_active_request, test_status_reports_model_lifecycle_state — supported

## State transitions

- **t_init** `ModelManager.__init__`: `backend_loaded := false`, `active_requests := 0`, `last_used_set := false`, `timer_pending := false`, `unloaded := false` — VERIFIED
- **t_initialize** `ModelManager.initialize`: `backend_loaded := true` — supported
- **t_begin** `ModelManager._begin_request`: `active_requests := active_requests + 1` — VERIFIED
- **t_end** `ModelManager._end_request`: `active_requests := max(0, active_requests - 1)`, `last_used_set := true` — VERIFIED
- **t_cancel_clear** `ModelManager._cancel_idle_unload_timer`: `timer_pending := false` — VERIFIED
- **t_schedule_arm** `ModelManager._schedule_idle_unload_timer_locked`: `timer_pending := true` — VERIFIED
- **t_load_touch** `ModelManager.load_model`: `last_used_set := true` — VERIFIED
- **t_unload_backend** `ModelManager._unload_backend_locked`: `backend_loaded := false`, `last_used_set := true`, `unloaded := true` — VERIFIED
- **t_unload_noop** `ModelManager._unload_backend_locked`: `unloaded := false` — supported
- **t_unload_all** `ModelManager.unload_all`: `backend_loaded := false` — supported

## Procedures (composition)

- `ModelManager.__init__`: T:t_init — supported
- `ModelManager.initialize`: T:t_initialize — supported
- `ModelManager.ensure_backend`: D:d_eb_fast → D:d_eb_locked — supported
- `ModelManager.get_backend`: D:d_get_backend — supported
- `ModelManager.load_model`: D:d_load_guard → T:t_load_touch → call:ModelManager._schedule_idle_unload_timer_locked — supported
- `ModelManager._cancel_idle_unload_timer`: D:d_cancel → T:t_cancel_clear — supported
- `ModelManager._unload_backend_locked`: D:d_unload_guard → T:t_unload_backend — supported
- `ModelManager._schedule_idle_unload_timer_locked`: call:ModelManager._cancel_idle_unload_timer → call:ModelManager._auto_unload_enabled → D:d_schedule → T:t_schedule_arm — supported
- `ModelManager._idle_unload_after`: call:ModelManager._auto_unload_enabled → D:d_idle_guard → call:ModelManager._auto_unload_timeout → D:d_idle_recent → call:ModelManager._unload_backend_locked → D:d_idle_unloaded — supported
- `ModelManager._begin_request`: T:t_begin → call:ModelManager._cancel_idle_unload_timer — supported
- `ModelManager._end_request`: T:t_end → call:ModelManager._schedule_idle_unload_timer_locked — supported
- `ModelManager.hold`: call:ModelManager._begin_request → call:ModelManager._end_request — supported
- `ModelManager.generate`: call:ModelManager._begin_request → call:ModelManager.ensure_backend → D:d_volume → call:ModelManager._end_request — supported
- `ModelManager.unload_all`: call:ModelManager._cancel_idle_unload_timer → D:d_unload_all — supported
- `ModelManager.unload`: call:ModelManager._cancel_idle_unload_timer → call:ModelManager._unload_backend_locked → D:d_unload_cuda — supported
- `ModelManager.reload`: call:ModelManager._cancel_idle_unload_timer → call:ModelManager._unload_backend_locked → call:ModelManager.initialize → call:ModelManager.load_model → call:ModelManager._schedule_idle_unload_timer_locked — supported
- `ModelManager.status`: call:ModelManager._auto_unload_timeout → D:d_status_last — supported

## Unknown / incomplete (as stated by the model)

- load_model omitted from ensure_backend's executable steps: Both tests that reach the lazy-reload path (concurrency test, test_generate_lazy_reinit_when_backend_none) patch load_model with a stand-in, so its real decision sites are not executed there. The real production path would additionally run d_load_guard (F) and schedule (cancel F; d_schedule T during a request because active_requests > 0). The branch 'calls' list still names load_model.
- Cancel predicate abstracted to timer_pending: br:be9c978e2166 also requires the task not to be done and not to be the current task. No shown case distinguishes these; a cancel invoked from inside the running timer (re-arm path of d_idle_recent) or on an already-finished task would evaluate F while timer_pending is true.
- Concurrency test cannot be generated sequentially: test_ensure_backend_serializes_concurrent_reloads interleaves five coroutines (four fast-path F then four locked re-checks F); the sequential scenario predicts one reload then four fast-path T. The log marks it not scored.
- idle_expired in test_generate_schedules_idle_unload_when_enabled: Assumed the 0.01s timer fires after >= 0.01s of idleness so it unloads on the first firing; event-loop early wakeup within clock resolution could instead take the re-arm branch once before unloading.
- Timing of the idle timer relative to request completion: Timer firings are modeled as explicit _idle_unload_after calls placed after the awaited sleep; in test_active_request_blocks_idle_unload no timer exists during the request (begin cancels, none scheduled), so no firing is modeled.
- status test setup and get_manager singleton: The status test source is truncated in the bundle; last_used_set=true and backend_loaded=true are taken from the observed state-in. get_manager (br:2f19fdb911a4) is not modeled because no test exercises it.
- Exception paths: Errors raised by backend.load_model, initialize or backend.generate (wrapped into RuntimeError) are not modeled; in particular a failing generate still runs _end_request via hold's finally.

## Generative check (state sequences)

Scenario → genome (procedures, decisions, transitions) → predicted decision outcomes at the genome's sites, in order, and predicted final bound state; compared exactly with what executed. Statuses were established from the shown tests only.

- exact on scored tests: 13/13
- exact on tests withheld from the model and the checker: 4/4
- the same genome with every transition removed (stateless ablation): 3/13
