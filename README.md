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
uvx copier copy --trust gh:climate-resource/copier-bookshelf-dataset $path_to_my_new_repo
```

Copier will use the latest tagged release for generating a new project. If you wish to
use a specific commit/tag the `--vcs-ref` flag can be used (`--vcs-ref HEAD` will use
the most recent commit).

It will ask you lots of questions about the dataset you want to create.

Once you have created your repository, there are then a number of further
steps which have to be done to get everything running as intended.

## What the template scaffolds

A generated feedstock is a working feedstock, not a blank slate.
It ships a recipe declaring one book, a checked-in example input under `inputs/`,
and a `build.py` that reads it, processes it and writes one timeseries.
`make run` records and validates it offline, before a line of real code is written.

## Worked examples

The SDK ships a set of miniature feedstocks, each proving one thing, with the bundle it
should produce checked in beside it:
[climate-resource/bookshelf/examples](https://github.com/climate-resource/bookshelf/tree/feat/adopt-bookshelf-sdk/examples).

The scaffold is closest to `checked-in-data`.
The others are what a feedstock grows into:

| Example                 | What it proves                                                    |
| ----------------------- | ----------------------------------------------------------------- |
| `simple`                | The smallest legal recipe, with no inputs and no network.          |
| `checked-in-data`       | A resource addressed by `path:`, hashed by the recorder.           |
| `fetch-from-web`        | One upstream url, digest verified and cached.                      |
| `multi-version`         | One recipe, several upstream versions, selected by `--version`.    |
| `complex-processing`    | Several outputs and a real `used=` graph across steps.             |
| `defaults-and-overrides`| Inheriting from `defaults:`, then overriding some.                 |
| `mixed-visibility`      | A public book carrying one hidden resource.                        |
| `figures`               | A png attached as a document entry.                                |
| `reissue`               | Same version, changed processing.                                  |
| `low-level-api`         | A plain script that records for itself, with no recipe.            |

The [recipe format](https://github.com/climate-resource/bookshelf/blob/feat/adopt-bookshelf-sdk/docs/explanation/recipe-format.md)
documents every field a recipe can carry.
Until the SDK is released the template pins it to the `feat/adopt-bookshelf-sdk` branch,
so a generated feedstock and these examples are always the same code.

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

The steps are inlined rather than delegated to a shared reusable workflow.
GitHub does not let a public repository resolve actions or reusable workflows
that live in a private repository, and this repository is public,
so the steps live directly in the workflow instead.

For a generated feedstock, publishing that draft release by hand is what triggers the feedstock publish workflow.
A release published by CI would not fire it,
because releases created with `GITHUB_TOKEN` do not trigger other workflows.

No `PERSONAL_ACCESS_TOKEN` is needed.
The bump workflow uses the built-in `GITHUB_TOKEN`.

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
