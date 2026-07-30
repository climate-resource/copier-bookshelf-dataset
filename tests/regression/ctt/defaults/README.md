# Example Dataset

Test project made with copier-template-tester

This repository contains the code to generate the Example Dataset book
for the [bookshelf](https://github.com/climate-resource/bookshelf).

## Getting started

Install the local virtual environment:

```bash
   make virtual-environment
```

The slim record recipe is in `bookshelf.yaml`.
The source code that builds the book is in `build.py`.


The book can be recorded using `make run`.
This creates a validated local bundle in `bundle/` without API credentials.

The bundle can be replayed to the Bookshelf API using `make publish`.
The publish workflow normally performs that step on a release.

Publishing uses the repository environment named `deploy`.
Configure `BOOKSHELF_CLIENT_ID` and `BOOKSHELF_CLIENT_SECRET` as environment secrets on that environment.
Set the public `BOOKSHELF_TOKEN_URL` repository variable to the WorkOS AuthKit token endpoint.
The generated publish caller uses `secrets: inherit`.
The reusable publish job carries `environment: deploy`, so those environment secrets are resolved when that job starts.

Identical inputs must create identical data bytes and stable lineage identifiers.
Change the hardcoded `version` in `build.py` when publishing a new data version.

The recorded bundle also carries the executed notebook, so its bundle hash covers the build source.
Any edit to `build.py`, a comment included, produces a new bundle hash.
Publishing after a source-only edit therefore creates a new edition whose data is unchanged.

## Releasing

Dispatch the "Bump version" workflow and pick a bump rule.
It bumps the version with `uv version`, builds the CHANGELOG with towncrier, tags,
and drafts the GitHub release, all in one run.

Publishing that draft release by hand is what triggers the publish workflow.
A release published by CI would not fire it,
because releases created with `GITHUB_TOKEN` do not trigger other workflows.
