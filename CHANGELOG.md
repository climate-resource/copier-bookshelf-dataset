# Changelog

Versions follow [Semantic Versioning](https://semver.org/) (`<major>.<minor>.<patch>`).

Backward incompatible (breaking) changes will only be introduced in major versions
with advance notice in the **Deprecations** section of releases.

<!--
You should *NOT* be adding new changelog entries to this file,
this file is managed by towncrier.
See `changelog/README.md`.

You *may* edit previous changelogs to fix problems like typo corrections or such.
To add a new changelog entry, please see
`changelog/README.md`
and https://pip.pypa.io/en/latest/development/contributing/#news-entries,
noting that we use the `changelog` directory instead of news,
markdown instead of restructured text and use slightly different categories
from the examples given in that link.
-->

<!-- towncrier release notes start -->

## copier-bookshelf-dataset v0.3.0b1 (2026-08-31)

### Improvements

- Raised the scaffolded `bookshelf` floor to 1.0.0b2.
  A checked-in `path:` input records its bytes from that release, so an earlier one generates a
  feedstock that records and validates but cannot publish. ([#22](https://github.com/climate-resource/copier-bookshelf-dataset/pull/22))
- Added `alpha` and `beta` to the bump workflow's version rules,
  so a feedstock can cut a pre-release without editing the workflow first. ([#23](https://github.com/climate-resource/copier-bookshelf-dataset/pull/23))

### Bug Fixes

- Pivoted the scaffolded build to wide before writing its timeseries.
  The platform stores a timeseries with one column per year, so the long frame the scaffold
  produced was recorded and validated happily and then refused at publish. ([#22](https://github.com/climate-resource/copier-bookshelf-dataset/pull/22))

### Improved Documentation

- Added a release pilot runbook and `scripts/release-pilot.sh`, which drives a tagged template release
  through the `bookshelf-test` feedstock and checks the book reached the API.

  Documented that a feedstock's first publish needs its volume created once with
  `bookshelf volume create`, which `bookshelf publish` will not do for you. ([#22](https://github.com/climate-resource/copier-bookshelf-dataset/pull/22))


## copier-bookshelf-dataset v0.3.0a1 (2026-08-28)

### Breaking Changes

- Replaces the `pdm bump` release process with a `uv version` bump.

  - The `Bump version` workflow now bumps, builds the changelog, tags and drafts the release in a single dispatch, so `release.yaml` is gone.
  - Bump rules changed from the `pdm-bump` vocabulary to `uv version --bump` segments, for example `no-pre-release` becomes `stable`.
  - `scripts/get-version.py`, `scripts/changelog-to-release-template.py` and the local `.github/actions/setup` composite are gone. The bump workflow covers all three itself.
  - A `PERSONAL_ACCESS_TOKEN` is no longer required for bumping. The bump runs on the built-in `GITHUB_TOKEN`.

  Run `copier update` to pick this up. Templated repositories should delete their own `release.yaml` and `scripts/get-version.py` if the update leaves them behind.

  ([#10](https://github.com/climate-resource/copier-bookshelf-dataset/pull/10))
- Moves the generated feedstock onto the Bookshelf SDK that now lives in the `bookshelf` package.

  - The dependency is `bookshelf[publish,dataframes]>=1.0.0b1`, taken from PyPI.
  - `build.py` calls `bookshelf.setup()` for its client and draft, so the collection, licence, visibility and authors come from `bookshelf.yaml`.
  - The build carries a single activity block, which is all a recorded build supports.
  - Recording, validating and replaying a bundle run through the `bookshelf` CLI.
  - Scaffolding sets the origin remote, writes `uv.lock` and makes the first commit, because recording derives provenance from git and CI syncs with `--locked`.

  ([#11](https://github.com/climate-resource/copier-bookshelf-dataset/pull/11))
- Drops every bundle script in favour of the `bookshelf` CLI, which now ships `record`, `validate` and `publish`.

  - `template/scripts/` is gone. `make run` calls `uv run bookshelf record --force` then `uv run bookshelf validate`, and `make publish` calls `uv run bookshelf publish`.
  - Adds a `make publish-dry-run` target, so a maintainer can see which edition a bundle resolves to before publishing to production.
  - The `record-bundle` composite action keeps only `cache_key.py`. Its `record_bundle.py`, `validate_bundle.py` and `publish_bundle.py` helpers are gone, and so is the `BOOKSHELF_ACTION_PATH` export that existed to reach them.
  - The publish workflow passes `--api-url` instead of `--base-url` and no longer passes `--token`. The CLI reads the credential from `BOOKSHELF_TOKEN`, so it never reaches argv or the job log.
  - Local `make run` and the CI action now perform identical validation, because both call the same strict `bookshelf validate`.

  A generated feedstock carries no Python of its own beyond `build.py`.

  Run `copier update` to pick this up. Templated repositories should delete their own `scripts/` directory if the update leaves it behind.

  ([#12](https://github.com/climate-resource/copier-bookshelf-dataset/pull/12))
- Moves the template onto the sectioned recipe and the `Build` helpers of the current SDK.
  `bookshelf.yaml` now carries `volume:`, `defaults:`, `build:` and `books:`,
  and `build.py` calls `bookshelf.setup()` once, reads its input through `build.use("raw")`
  and writes its output with `build.book.write(..., used=[raw])`.

  `bookshelf record` requires `--version`, so a bundle holds one book and lands in `bundle/<version>`.
  `make run`, `make publish` and `make publish-dry-run` take `VERSION=vX.Y.Z`, defaulting to `v0.1.0`. ([#19](https://github.com/climate-resource/copier-bookshelf-dataset/pull/19))
- Takes the SDK from PyPI rather than from a git branch, now that `1.0.0b1` is published.
  The generated `pyproject.toml` depends on `bookshelf[publish,dataframes]>=1.0.0b1`
  and carries no `[tool.uv.sources]`.
  The specifier names the beta, because a bare one would resolve to the last stable release. ([#20](https://github.com/climate-resource/copier-bookshelf-dataset/pull/20))
- Drops the Copier tasks in favour of a `make initial-setup` target in the generated feedstock.

  Tasks force `--trust` on every `copier copy` and `copier update`,
  which stops Renovate applying a template release to a feedstock on its own.
  `make initial-setup` does the same work, guarded the same way,
  so re-running it on an existing repository still changes nothing.
  Run it once after generating a feedstock. ([#21](https://github.com/climate-resource/copier-bookshelf-dataset/pull/21))

### Features

- Replaced the legacy producer scaffold with deterministic record and replay feedstocks that delegate execution to version matched Bookshelf actions colocated with the Copier template. ([#9](https://github.com/climate-resource/copier-bookshelf-dataset/pull/9))
- Scaffolds a working feedstock rather than a blank slate.
  A generated project ships a checked-in example input under `inputs/raw.csv`,
  a recipe declaring one book that reads it,
  and a build file that processes it and writes one timeseries.
  `make run` records and validates that bundle offline, before any real code is written. ([#19](https://github.com/climate-resource/copier-bookshelf-dataset/pull/19))
- Adopts the processes from `copier-python-service`:

  - A generated feedstock ships a `renovate.json` with the Copier, pre-commit and `pep621` managers switched on,
    so a template release reaches it as a pull request.
  - This repository has a `renovate.json` of its own, with custom managers for the pins inside `template/`.
  - A `Regenerate fixtures` workflow runs `ctt` on a Renovate pull request and pushes the result back,
    because Renovate only edits `template/`.
  - `tests/test_rendered.py` renders every `ctt.toml` case from the working tree, lints it,
    validates its workflows and pre-commit config, and checks the live render against the committed fixture.
  - `make test-fast` skips the slow rendered-feedstock checks, and `make test` runs everything in parallel.

  ([#21](https://github.com/climate-resource/copier-bookshelf-dataset/pull/21))

### Improvements

- Refreshed the toolchain after a long gap.

  - Raised the Python floor to 3.12 for the template and for generated feedstocks, and dropped the dead 3.10 entry from the test matrix.
  - Updated the pre-commit hooks, the pinned `ruff` version and `copier-template-tester` to current releases.
  - Moved dev dependencies to `[dependency-groups]`, which replaces the deprecated `tool.uv.dev-dependencies`.
  - Pinned `actions/checkout`, `actions/cache` and `actions/upload-artifact` to v6.

  ([#10](https://github.com/climate-resource/copier-bookshelf-dataset/pull/10))
- Records and publishes every version the recipe declares.
  Publishing an unchanged book is idempotent, so a version that has not moved keeps its edition.
  Pass a `version` input to either workflow to narrow the run to one book.

  Points the CI input cache at the directory the SDK actually fetches into.
  `BOOKSHELF_CACHE_DIR` now selects the workspace, because the SDK's default is a platform
  cache directory that no runner keeps between jobs. ([#19](https://github.com/climate-resource/copier-bookshelf-dataset/pull/19))
- Points the bump workflows at the shared `climate-resource/github-actions` bump workflow,
  rather than inlining the steps.
  The shared repository is now public, so both this repository and the generated feedstocks can call it. ([#21](https://github.com/climate-resource/copier-bookshelf-dataset/pull/21))

### Bug Fixes

- Fixes `actions/record-bundle` so it calls `astral-sh/setup-uv` directly rather than through a wrapper.
  This repairs the composite for the public feedstocks that consume it. ([#10](https://github.com/climate-resource/copier-bookshelf-dataset/pull/10))
- Fixed a generated feedstock being unable to publish.

  The recipe declared the book `public` while the recorder registered every resource as `hidden`,
  so the API refused the bundle with `Book visibility 'public' is wider than at least one member resource`.
  Two of those resources are the `build.ipynb` and `build.html` documents the recorder adds itself,
  so an author could not fix this from `build.py`.

  The fix landed upstream rather than here:

  - `bookshelf` now records every resource at the book's tier, the recorder's own documents included.
  - `bookshelf-platform` no longer requires a book to be as narrow as its narrowest member.

  So the template keeps `visibility: public` and a fresh feedstock publishes out of the box.
  A book and its resources now carry independent tiers,
  so passing `visibility=` on one `activity.register(...)` call holds that resource back from an otherwise public book.

  ([#15](https://github.com/climate-resource/copier-bookshelf-dataset/pull/15))
- Fixed two problems that only appear once a second feedstock is generated from the template.

  - The example input was a fixed literal, so every feedstock registered byte identical resources.
    Registration deduplicates on content, so the second feedstock to publish into a deployment aliased onto
    the first one's resources and then failed to attach them.
    The example now carries a `dataset` column naming the feedstock,
    and `input_sha256` is computed from those bytes rather than hardcoded.
  - Free text answers reached `towncrier.toml`, `pyproject.toml` and `bookshelf.yaml` unescaped,
    so an answer containing a double quote produced a file that does not parse.
    In the case of `dataset_name_human` that broke every changelog build.
    The validators also carried backslash escapes that Jinja does not understand,
    so answering either prompt raised a `DeprecationWarning`.

  ([#17](https://github.com/climate-resource/copier-bookshelf-dataset/pull/17))

### Improved Documentation

- The README now gives the full Git URL rather than the `gh:` shorthand.
  Copier records the URL in `.copier-answers.yml`, and Renovate can only look up tags on the full form. ([#21](https://github.com/climate-resource/copier-bookshelf-dataset/pull/21))


## copier-bookshelf-dataset v0.2.4 (2024-10-16)

### Features

- Include copier answers in templated repository ([#8](https://github.com/climate-resource/copier-bookshelf-dataset/pull/8))


## copier-bookshelf-dataset v0.2.3 (2024-10-16)

### Bug Fixes

- Include a pre-release dependency on bookshelf ([#7](https://github.com/climate-resource/copier-bookshelf-dataset/pull/7))


## copier-bookshelf-dataset v0.2.2 (2024-10-16)

### Improvements

- Provide a saner default for the project url ([#5](https://github.com/climate-resource/copier-bookshelf-dataset/pull/5))


## copier-bookshelf-dataset v0.2.1 (2024-10-15)

No significant changes.


## copier-bookshelf-dataset v0.2.0 (2024-10-15)

### Bug Fixes

- Fix the url in the towncrier configuration ([#3](https://github.com/climate-resource/copier-bookshelf-dataset/pull/3))

### Improved Documentation

- Fleshed out the README.md file with more information about the project. ([#1](https://github.com/climate-resource/copier-bookshelf-dataset/pull/1))

## copier-bookshelf-dataset v0.1.0 (2024-10-14)

### Features

- Initial development of the template based on github.com/climate-resource/bookshelf-rcmip-emissions ([#1](https://github.com/climate-resource/copier-bookshelf-dataset/pull/1))
- Add configuration to generate a changelog on release ([#1](https://github.com/climate-resource/copier-bookshelf-dataset/pull/1))
