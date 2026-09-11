# Copier - Bookshelf Dataset

This is our copier template for generation of new datasets for the [BookShelf](https://climate-resource.github.io/bookshelf/).
It is built to work with [copier](https://copier.readthedocs.io/en/stable/#quick-start).

The template itself lives in `template`.

# Installation


It is expected that `uv` is installed globally.
`uv` will then be used to manage the installation of `copier`
and other project dependencies.

Before getting started with development, you will need to install the virtual environment.

```
make virtual-environment
```

# Usage

To start a new repository run `copier` with our template:

```bash
uvx copier copy https://github.com/climate-resource/copier-bookshelf-dataset.git $path_to_my_new_repo
```

Use the full Git URL rather than the `gh:` shorthand.
Copier records it in `.copier-answers.yml`, and Renovate can only look up tags on the full form.

Copier will use the latest tagged release for generating a new project. If you wish to
use a specific commit/tag the `--vcs-ref` flag can be used (`--vcs-ref HEAD` will use
the most recent commit).

It will ask you lots of questions about the dataset you want to create.

Then run `make initial-setup` inside the new repository.
This does the `git init`, sets the origin remote, writes `uv.lock` and makes the first commit.
Recording derives provenance from git, so it needs all three.

Once the repository is on GitHub, give it the `bookshelf-feedstock` topic:

```bash
gh repo edit climate-resource/$my_new_repo --add-topic bookshelf-feedstock
```

That topic is how every feedstock is found: `gh search repos --owner climate-resource --topic bookshelf-feedstock`.

The template declares no Copier tasks, so plain `copier copy` and `copier update` work
without `--trust`, and Renovate can apply template updates to a feedstock on its own.
A generated feedstock ships a `renovate.json` with the Copier manager switched on.

## What the template scaffolds

A generated feedstock is a working feedstock, not a blank slate.
It ships a recipe declaring one book, a checked-in example input under `inputs/`,
and a `build.py` that reads it, processes it and writes one timeseries.
`make run` records and validates it offline, before a line of real code is written.

## Worked examples

The SDK's [examples README](https://github.com/climate-resource/bookshelf/blob/main/examples/README.md)
lists the example feedstocks and explains how to use them.
The [recipe format](https://github.com/climate-resource/bookshelf/blob/main/docs/explanation/recipe-format.md)
documents every field a recipe can carry.

## Feedstock automation

A bundle holds one book, so each version is recorded into its own `bundle/<version>` directory.
CI records every version the recipe declares, and the publish workflow replays every one of them.
Publishing an unchanged book is idempotent, so a version that has not moved keeps its edition.
Pass a `version` input to either reusable workflow to narrow that to one book.

The CI workflow validates a candidate rather than whatever was checked out:

- On a pull request, the candidate is the head merged with the current `main`.
  The `candidate` job pins that `main` commit,
  and every later job rebuilds the same merge and checks it gets the same tree.
  A merge conflict fails the run rather than recording either side.
- On any other event, the candidate is the commit being built.
- The candidate identity is uploaded as the `bookshelf-candidate` artifact.
  It holds the head SHA, the main SHA and the merged tree.
- The `targets` job lists one target per `(volume, version)` across the `recipes` input.
  The input defaults to `bookshelf.yaml`.
  It uploads the list as `bookshelf-targets`.
  It fails on an empty list or on a target that two recipes both declare.
- The `record` job records and validates each target in its own matrix leg.
  Each leg uploads `bookshelf-bundle-<volume>-<version>`,
  holding the bundle and an `outcome.json` that says `validated` or `failed`.
- The `candidate outcome` job always runs.
  It passes only when every target has exactly one `validated` outcome and every job before it succeeded,
  so a skipped or cancelled leg counts as a failure.
  It writes a table of the outcomes to the job summary.
- The `upload preview` job stores the candidate's books on the platform for reviewers.
  It is the only job granted `id-token: write`,
  so it proves who it is with the run's GitHub Actions OIDC token rather than a credential.

The preview job never checks the feedstock out.
Pull request code is untrusted, and any step in a job that can mint the token can use it,
so the job checks out only this template's helpers and installs the SDK from the index.
The `sdk-version` input is the exact `bookshelf` version it installs, and it is required.
The `api-base-url` input picks the deployment, defaulting to production.
A target that never produced a bundle fails the job without uploading,
so the platform's check stays at "expected" and still blocks the merge.
A pull request from a fork skips the job,
because a fork cannot mint a token for the upstream repository.
The platform's check tells the author that forks are unsupported.

None of these jobs holds a secret or a write credential.
The feedstock checkouts keep the read-only `GITHUB_TOKEN`,
so the jobs can fetch `main` and any blobs the merge needs.
The required check is the platform's `Bookshelf / validate publication`, not `candidate outcome`.
The platform also posts the pull request comment and publishes.
A candidate is only as fresh as the `main` it was merged with,
so readiness relies on the feedstock ruleset requiring branches to be up to date before merging.

This public repository hosts the reusable feedstock workflows in `.github/workflows/feedstock-ci.yaml` and `.github/workflows/feedstock-publish.yaml`.
Their composite action lives in `actions/record-bundle`.
Generated callers pin the reusable workflows to the exact Copier ref that generated the feedstock.
The reusable workflow then checks out its composite action from the workflow's own commit, so the caller, workflow, and action cannot drift apart.

A feedstock's first publish needs its volume created once with `bookshelf volume create`.
`bookshelf publish` will not create one, so without it the publish workflow fails
with `Series 'NAME' not found`.

Publishing uses the feedstock repository environment named `deploy`.
Configure `BOOKSHELF_CLIENT_ID` and `BOOKSHELF_CLIENT_SECRET` as environment secrets on that environment.
Set the public `BOOKSHELF_TOKEN_URL` repository variable to the WorkOS AuthKit token endpoint.
Generated publish callers use `secrets: inherit`.
The reusable publish job carries `environment: deploy`, so those environment secrets are resolved when that job starts.

## Releasing

Version bumps and releases run through `.github/workflows/bump.yaml`.
Dispatch the "Bump version" workflow and pick a bump rule.
The workflow bumps the version with `uv version`, builds the CHANGELOG with towncrier,
tags, and drafts the GitHub release in a single run.

The work is delegated to the shared `climate-resource/github-actions` bump workflow,
so both this repository and every generated feedstock call the same thing.

For a generated feedstock, publishing that draft release by hand is what triggers the feedstock publish workflow.
A release published by CI would not fire it,
because releases created with `GITHUB_TOKEN` do not trigger other workflows.

The bump workflow needs no `PERSONAL_ACCESS_TOKEN`, because it runs on the built-in `GITHUB_TOKEN`.

Consumers pick a template release up with `copier update --vcs-ref v1.2.3`,
or let Renovate open the pull request for them.

A green test suite proves the render is valid, not that the rendered feedstock still works
against a live Bookshelf.
The [release pilot](docs/runbooks/release-pilot.md) closes that gap.
It drives a tagged release through the `bookshelf-test` feedstock and asks the API what landed:

```bash
bash scripts/release-pilot.sh --template-ref v1.2.3
```

## Updating repositories

If you need to update your repository,
simply navigate to your repository and run `copier update`.
If you don't want to go through all the questions again
(the default answers are taken from last time you answered the questions),
use `copier update --force` instead.

By default, copier will use the most recent tag when updating the repository.
If you wish to use the current HEAD commit for your update,
run `copier update --vcs-ref=HEAD`.
This `--vcs-ref` option can also be used to specify a specific tag to apply.

When you update, there will likely be merge conflicts,
particularly in`pyproject.toml` related to versions.
If you use the `--conflict inline` option with `copier update` then the diffs should be inline
(see [here](https://copier.readthedocs.io/en/stable/updating/)).
The pre-commit config will make sure you don't miss conflicts and accidentally commit merge conflict lines.

Any conflicts related to the `uv.lock` file can be safety ignored and a `uv lock`
should be run after updating to regenerate the lockfile
(The pre-commit flow should catch this error).

# Template Development

## Copier template tester (ctt)

We use [copier template tester (ctt)](https://copier-template-tester.kyleking.me/)
to generate the output of using our template.
This output is stored in the `tests/regression/ctt` folder which is tracked by git
and automatically updated by our pre-commit hooks.
This folder provides a way for us to easily see the impact that changes to our template
have on generated repositories under different possible answers to our copier questions.

Put another way, ctt provides a pure regression test of our template,
making sure that any changes to the output it generates are immediately obvious
and trackable over different commits.

Run `make ctt` whenever `copier.yaml` or `template/` changes and commit the result.
The tests render from that committed output, so a stale copy fails CI.
On a Renovate pull request the `Regenerate fixtures` workflow runs `ctt` and pushes the
result back onto the branch, because Renovate only edits `template/`.
That push needs the organisation `PERSONAL_ACCESS_TOKEN` secret,
because a `GITHUB_TOKEN` push would not re-run CI on the branch.

## Tests

```bash
make test       # everything, including the slow rendered-feedstock checks
make test-fast  # skip the slow ones
```

`tests/test_rendered.py` renders every `ctt.toml` case from the working tree,
lints it with `ruff`, checks its workflows with `actionlint`,
validates its pre-commit config, parses its `renovate.json`,
and checks the live render against the committed fixture.
It takes a few minutes, which is the price of knowing every render actually works.

The remaining tests are fast contract checks over the committed fixtures:
the copier questions and their validators, the composite action's inputs,
the cache key, the generated metadata and the feedstock layout.
