# third_party

Pinned upstream sources, fetched by `scripts/fetch_third_party.sh` (git-ignored until `git init`,
then added as submodules at the same tags).

| Repo | Tag | Used for |
|---|---|---|
| PegasusSimulator | **PR #144 head `fcb99c0`** (Isaac Sim 6.0 migration, branch `dev_6.0.1` lineage; **not a release tag** — `v5.1.0` was the Isaac 5.1 pin). Fetch: `git fetch origin refs/pull/144/head:pr144`; the `local` branch sits on it | `bisg/sim` builds **from** this submodule (`docker/sim/Dockerfile`), not a fresh clone — local edits here reach the image |
| zed-ros2-wrapper | `v5.4.1` (ZED SDK 5.4.1) | its `docker/` build scripts (run directly against this submodule) produce our `bisg/zed` images |
| PX4-Autopilot (optional, `WITH_PX4=1`) | see `PX4_TAG` in `config/bisg.conf` | reading `px4-rc.*`, param names, `px4_fmu-v4` build for the Pixracer — not a submodule, cloned fresh inside the sim image build |

## Local edits, kept updatable

No push access upstream and no fork wanted → local edits live on a **local git branch** inside
each submodule, never on `main`/`master`, never pushed. Both submodules already have one
(`git branch -vv` inside them to check) checked out at the pinned tag.

```bash
# One-time, if a submodule is still on a bare tag instead of the `local` branch:
git -C third_party/PegasusSimulator checkout -b local pr144   # was: v5.1.0 before the Isaac 6.0 migration

# Make your edit, commit it on that branch:
$EDITOR third_party/PegasusSimulator/<file>
git -C third_party/PegasusSimulator commit -am "local: <what changed and why>"

# Pin the outer repo to that commit (this is what actually gets built):
git add third_party/PegasusSimulator
git commit -m "pin PegasusSimulator to local branch (+<setting>)"
```

`docker compose build sim` and `docker/zed/build.sh` always build whatever is currently checked
out in the submodule, so this takes effect immediately on the next build — no patch files, no
scripts.

**Picking up a new upstream tag** without losing your edit:

```bash
git -C third_party/PegasusSimulator fetch origin
git -C third_party/PegasusSimulator rebase v5.2.0     # replays your local commit(s) on top
git add third_party/PegasusSimulator
git commit -m "bump PegasusSimulator to v5.2.0 (+local setting)"
```

Same shape for `zed-ros2-wrapper`. Resolve any rebase conflict right there, same as rebasing any
small branch. `.gitmodules` never changes. Bumping the tag this way still needs the usual
pin-change ADR update per CLAUDE.md; adding or refreshing a commit on `local` does not.

Never `git submodule update --remote` (CLAUDE.md) — that silently moves the pin without going
through this fetch/rebase/commit sequence.
