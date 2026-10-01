# Sandbox: security contract and backends

Target code (the repository's tests, generated probes) only runs through
`Workspace.run` → `select_backend()` → a platform backend. Collectors (Python, Node, Go)
never see which backend is active; `diffgenome change` logs it (`sandbox: <name>`) and
refuses to run, with the reason, when none is usable.

## Contract (tests/test_sandbox_invariants.py, same suite for every backend)

| invariant | macOS `macos-seatbelt` | Linux `linux-bubblewrap` |
|---|---|---|
| no external TCP / UDP | `(deny network*)` | own network namespace (only its loopback) |
| `--allow-loopback` | bind/inbound/outbound `localhost:*`, **including host services** | loopback inside the sandbox only; host services unreachable |
| host unix sockets | denied (`network*`) | `/tmp`, `/run`, `/var/tmp` private (docker, agents hidden); see limits |
| writes | workspace only (+ `/dev/null`, tty) | read-only root; workspace bound writable; private `/tmp`, `/run`, `/var/tmp`, `/dev` |
| original repository | read-only (outside the workspace) | read-only |
| reads | everywhere | everywhere except private dirs; top-level `/tmp` entries a command names (its venv) are bound back read-only |
| environment | scrubbed (PATH=/usr/bin:/bin, HOME/TMPDIR in the workspace, explicit extras only) | same |
| child processes | inherit the profile | inherit the namespaces |
| other processes | `signal (target self)` only | own PID namespace |
| limits | CPU 600 s, 4096 processes, 1 GiB files (setrlimit), wall-clock timeout | same |
| violations | blocked (EPERM); socket attempts also recorded by the Python egress guard | blocked (EROFS/ENETUNREACH); same guard |
| no backend | refuse to run | refuse to run (reason + fix hint) |

Not covered by the sandbox in either backend (unchanged from 0.1.x): DiffGenome's own helpers
that read target source before tests run (`go env`, building and running the Go instrumenter,
Node's `instrument.js` with the target's TypeScript) run unsandboxed.

## Linux options considered (GitHub `ubuntu-latest`, Ubuntu 24.04, kernel 6.17)

| option | result on a stock runner | fit |
|---|---|---|
| bubblewrap | not installed; with apt it fails until unprivileged user namespaces are allowed (AppArmor `apparmor_restrict_unprivileged_userns=1`) | **chosen**: one small tool gives net + mount + PID isolation; ~1.5 ms (local) / ~6 ms (runner) per command |
| `unshare` (util-linux) | preinstalled; same user-namespace block | needs our own mount setup for write confinement |
| Landlock | available unprivileged (ABI 7) | filesystem only; network rules are per port, not address, and do not cover UDP or unix sockets: cannot express "loopback only" |
| docker / podman | available (docker group = root-equivalent) | heavy; dependencies must be mounted in; host loopback unreachable with `--network none` |
| slirp4netns / pasta | installed | need user namespaces too; would only add host-port forwarding |

Requirements on Linux: `bubblewrap`, and unprivileged user namespaces. Debian, Fedora and
Ubuntu 22.04 allow them by default; Ubuntu 24.04 needs
`sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0` (GitHub-hosted runners allow
it; sydes-action does it for runtime evidence on Linux runners).

## Remaining limits

- Linux `--allow-loopback` does not reach host services (e.g. a PostgreSQL started by the CI
  job on 127.0.0.1). Tests that need one run on macOS today, or need a port relay (not built).
- Linux: pathname unix sockets outside `/tmp`, `/run`, `/var/tmp` stay connectable when file
  permissions allow (macOS denies all unix sockets).
- Linux inside Docker: bwrap needs the container to permit user namespaces and a fresh `/proc`
  (`--security-opt seccomp=unconfined --security-opt systempaths=unconfined`); ordinary VMs
  and GitHub-hosted runners do not need this.
