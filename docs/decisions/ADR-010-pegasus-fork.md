# ADR-010 — Pegasus from our own fork (branch `local`)

Status: accepted (2026-10-15)

## Context
The Pegasus pin is PR #144's head (`fcb99c0`, the Isaac Sim 6.0 port), reachable upstream only as `refs/pull/144/head`
(migration-errors M18). Local edits live on a `local` branch inside the submodule (`docs/sources.md`), but that branch was never
pushed: the first local commit (`08c9954`, the IMU noise fix of upstream PR #148) made the superproject point at a commit no other
machine can fetch, so Workstation B could not `git submodule update`. We have no push access upstream.

## Decision
- A fork, **`github.com/akashshingha850/PegasusSimulator`**, carries branch **`local`** = PR #144 + our local commits. It is the
  submodule URL (`.gitmodules`, `branch = local`) and `PEGASUS_REPO`; upstream stays reachable as `PEGASUS_UPSTREAM` (remote
  `upstream` in the submodule) for rebasing onto a future release.
- Pin form `PEGASUS_TAG=local-<sha>` (`scripts/fetch_sources.sh` clones the fork's `local` branch and checks out that SHA). The
  superproject's submodule commit is the real pin; the tag in `config/bisg.conf` names it.
- Every new local commit is pushed to the fork **before** the superproject commit that points at it, so any machine can fetch it.
- Only `local` is maintained on the fork; its `main` is GitHub's copy of upstream and is not used.

## Consequences
- Workstation B (and any fresh clone) syncs with `git pull && git submodule sync && git submodule update --init docker/sim/PegasusSimulator`,
  then `./bisg build sim`.
- M18 is closed: the pinned history no longer depends on the PR ref surviving upstream.
- Rebasing onto an upstream tag is unchanged (`docs/sources.md`), plus a force-push of `local` to the fork; a tag bump still needs
  a `docs/plan.md` §4 update.
