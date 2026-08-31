# Release pilot

Every template release changes what a feedstock looks like.
A green test suite proves the render is valid, not that the rendered thing still works
against a live Bookshelf.
This runbook closes that gap.

It takes a tagged release of this template, drives it through
[`bookshelf-test`](https://github.com/climate-resource/bookshelf-test),
and asks the API what landed.

`scripts/release-pilot.sh` runs the whole thing.
Read this page once, then use the script.

## What the pilot proves

Each step exercises one thing a template change can break:

- `copier update` still applies to an existing feedstock without conflicts.
- The rendered `Makefile`, `build.py` and recipe still record and validate a book offline.
- The generated bump workflow still tags and drafts a release.
- The generated publish caller still resolves the `deploy` environment secrets,
  exchanges the M2M credential, and replays the bundle.
- The book is on the API afterwards, published, with its resources attached.

## Prerequisites

- `gh` authenticated against `climate-resource`, with write access to `bookshelf-test`.
- `uv`, `jq` and `git` on `PATH`.
- A clone of `bookshelf-test` next to this repository, on `main` and level with `origin/main`.
- The `deploy` environment on `bookshelf-test` carrying `BOOKSHELF_CLIENT_ID`
  and `BOOKSHELF_CLIENT_SECRET`, and the `BOOKSHELF_TOKEN_URL` repository variable set.
  These are configured once and outlive any single pilot.
- The volume already created on the API.
  A first publish into a new volume fails with `Series 'NAME' not found`,
  because `bookshelf publish` will not create one.
  Create it once with `uv run bookshelf volume create test --licence MIT`.
- A live Bookshelf credential, because the book is recorded as hidden.
  Run `uv run bookshelf auth login` in the feedstock.
  A stored credential that cannot refresh drops the client to anonymous without saying so,
  which reads a hidden volume as an empty one.
  Preflight refuses to start in that state rather than take a false baseline.

## Running it

Cut the template release first.
Dispatch the "Bump version" workflow on this repository, then publish the draft release
it leaves behind.
The pilot needs a real tag, because that is what a feedstock pins to.

Then:

```bash
bash scripts/release-pilot.sh --template-ref v0.3.0
```

Leave `--template-ref` off to pilot the latest release.

The script prompts before the two steps that reach the outside world:
pushing to `main`, and publishing the draft release.
Pass `--yes` to skip both prompts once you trust the run.

Each run leaves its state under `$XDG_STATE_HOME/release-pilot/`, so `--from` resumes against
what the earlier invocation actually saw rather than guessing.
Everything in there is derived, so deleting it costs only a full run.

## The steps

The script runs these in order.
`--from` and `--to` select a slice of them, which is how you resume after a stop.

| Step | What it does |
| --- | --- |
| `preflight` | Checks the tools, the auth, the clean worktree and that the template tag exists. |
| `update` | Runs `copier update --vcs-ref <tag> --conflict inline`, then relocks. |
| `record` | Runs `make run VERSION=...`, recording and validating the book offline. |
| `push` | Commits the update and pushes it to `main`. |
| `bump` | Dispatches the feedstock's "Bump version" workflow and follows the run. |
| `release` | Publishes the draft release the bump left, which is what fires the publish workflow. |
| `publish` | Follows the "Feedstock publish" run to its exit code. |
| `verify` | Resolves the book on the API, checks it is published, and checks the volume gained an edition. |

## When a step fails

The script stops at the first failure and names the command that will show you why.

- **Conflict markers after `update`.**
  The template moved a file the feedstock had edited by hand.
  Resolve them, commit, then re-run with `--from record`.
- **`record` fails.**
  The template's generated build no longer works.
  This is a template bug, so fix it here and cut a new release rather than patching the feedstock.
- **The bump run fails.**
  Usually a missing changelog fragment.
  Add one under `changelog/` in the feedstock.
- **The publish run fails at "Replay bundles" with `Series 'NAME' not found`.**
  The volume does not exist on that deployment yet.
  Create it once with `bookshelf volume create`, then re-run with `--from publish`
  after re-running the failed workflow.
- **The publish run fails at "Exchange M2M credentials".**
  The `deploy` environment secrets or `BOOKSHELF_TOKEN_URL` are wrong.
  Nothing to do with the template.
- **`verify` says the book did not move.**
  Publishing an unchanged book is idempotent, so a release that changes nothing the bundle
  covers lands no new edition.
  The recorded bundle covers `build.py`, so most template releases do move it.
  One that only touches, say, the README will not.
  Re-run with `--allow-unchanged` when that is what you expect.
  Left alone it is a failure, because a publish that wrote nothing proves only that the
  workflow ran, not that it can write.

## After a good pilot

The release is safe to roll out.
Renovate opens the `copier update` pull requests on the real feedstocks on its own.

## After a bad one

Do not leave a broken tag as the latest release.
Fix the template, cut a new patch release, and pilot that one.
