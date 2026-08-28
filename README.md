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

This public repository hosts the reusable feedstock workflows in `.github/workflows/feedstock-ci.yaml` and `.github/workflows/feedstock-publish.yaml`.
Their composite action lives in `actions/record-bundle`.
Generated callers pin the reusable workflows to the exact Copier ref that generated the feedstock.
The reusable workflow then checks out its composite action from the workflow's own commit, so the caller, workflow, and action cannot drift apart.

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
