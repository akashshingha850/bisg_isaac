# Pinned upstream sources

Live inside the Docker image folder that uses them: `docker/sim/PegasusSimulator` and `docker/zed/zed-ros2-wrapper` (git submodules),
`docker/zed/zed-isaac-sim` (plain clone, git-ignored). Fetched by `scripts/fetch_sources.sh`.

| Repo | Tag | Used for |
|---|---|---|
| PegasusSimulator | **our fork's `local` branch at `08c9954`** = PR #144 head `fcb99c0` (Isaac Sim 6.0 migration; **not a release tag** — `v5.1.0` was the Isaac 5.1 pin) + the IMU fix of upstream PR #148. Fork `github.com/akashshingha850/PegasusSimulator` (ADR-010), upstream as remote `upstream` | `bisg/sim` builds **from** this submodule (`docker/sim/Dockerfile`), not a fresh clone — local edits here reach the image |
| zed-ros2-wrapper | **our fork's `local` = `60f78bd`** (`ZED_WRAPPER_REF`; `ZED_WRAPPER_REPO` = github.com/akashshingha850/zed-ros2-wrapper, remote `upstream` = Stereolabs; ADR-011): upstream master `b19902d` (2026-10-07, v5.5.1-dev: the R9 fix of PR #460) + our fix = upstream PR #463, built against ZED SDK 5.4.1. Back to a tag once a release contains both | its `docker/` build scripts (run directly against this submodule) produce our `bisg/zed` images |
| zed-isaac-sim | `v5.2.1` = `529e538` (a **branch** upstream, so the SHA is the pin; Isaac Sim 6.0 line, has the ZED Mini twin `ZED_M`) | Stereolabs' Isaac Sim extension that streams a simulated ZED into the real SDK (`docs/zed-sdk-sim.md`). A plain clone, not a submodule (it holds a ~450 MB build tree); `docker/zed/build_isaac_ext.sh` builds it in place and widens its Kit range to 110.1.1 for the 6.0.0 image |
| PX4-Autopilot (optional, `WITH_PX4=1`) | see `PX4_TAG` in `config/bisg.conf` | reading `px4-rc.*`, param names, `px4_fmu-v4` build for the Pixracer — not a submodule, cloned fresh inside the sim image build |

## Local edits, kept updatable

No push access upstream → local edits live on a **local git branch** inside each submodule, never on `main`/`master`.
Pegasus' `local` branch is pushed to **our fork** (ADR-010), so every machine can fetch the pinned commit; the ZED wrapper's
has no local commits yet (push it to a fork the same way before its first one). `git branch -vv` inside a submodule to check.

**Pegasus, one-time per clone** (fresh clones get this from `scripts/fetch_sources.sh`):
```bash
git -C docker/sim/PegasusSimulator remote set-url origin https://github.com/akashshingha850/PegasusSimulator.git
git -C docker/sim/PegasusSimulator remote add upstream https://github.com/PegasusSimulator/PegasusSimulator.git
```

**Syncing another machine** (e.g. Workstation B) after a Pegasus change:
```bash
git pull && git submodule sync && git submodule update --init docker/sim/PegasusSimulator && ./bisg build sim
```

```bash
# One-time, if a submodule is still on a bare tag instead of the `local` branch:
git -C docker/sim/PegasusSimulator checkout -b local pr144   # was: v5.1.0 before the Isaac 6.0 migration

# Make your edit, commit it on that branch:
$EDITOR docker/sim/PegasusSimulator/<file>
git -C docker/sim/PegasusSimulator commit -am "local: <what changed and why>"
git -C docker/sim/PegasusSimulator push origin local            # Pegasus: to the fork FIRST, or other machines cannot fetch the pin

# Pin the outer repo to that commit (this is what actually gets built):
git add docker/sim/PegasusSimulator
git commit -m "pin PegasusSimulator to local branch (+<setting>)"
```

`docker compose build sim` and `docker/zed/build.sh` always build whatever is currently checked
out in the submodule, so this takes effect immediately on the next build — no patch files, no
scripts.

**Picking up a new upstream tag** without losing your edit:

```bash
git -C docker/sim/PegasusSimulator fetch origin
git -C docker/sim/PegasusSimulator rebase v5.2.0     # replays your local commit(s) on top
git add docker/sim/PegasusSimulator
git commit -m "bump PegasusSimulator to v5.2.0 (+local setting)"
```

Same shape for `zed-ros2-wrapper`. Resolve any rebase conflict right there, same as rebasing any
small branch. `.gitmodules` never changes. Bumping the tag this way still needs the usual
pin-change ADR update per CLAUDE.md; adding or refreshing a commit on `local` does not.

Never `git submodule update --remote` (CLAUDE.md) — that silently moves the pin without going
through this fetch/rebase/commit sequence.
