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

## copier-bookshelf-dataset v0.5.2 (2026-09-23)

### Features

- Feedstock CI now reads an organisation's private `bookshelf://` inputs with the workflow's own GitHub Actions token, so a recipe depending on an org-visible book or an uploaded file records in CI without a stored secret. This needs the Bookshelf GitHub App installed on the repository. ([#53](https://github.com/climate-resource/copier-bookshelf-dataset/pull/53))


## copier-bookshelf-dataset v0.5.0 (2026-09-21)

### Breaking Changes

- Removed the `Feedstock publish` reusable workflow, its generated caller and the `release: published` trigger.
  The platform now publishes a merged pull request from the sealed preview that passed its required check,
  so a feedstock needs no `deploy` environment and no M2M publish credential.
  A bump publishes its GitHub release rather than drafting it, because the release publishes no data.
  Deleted `docs/runbooks/release-pilot.md` and `scripts/release-pilot.sh` with the path they drove.
  Removed the bump workflow, towncrier configuration, changelog directory and dev dependencies from a generated feedstock.
  A feedstock cuts no releases, because the platform publishes on merge and the pull request is its record. ([#37](https://github.com/climate-resource/copier-bookshelf-dataset/pull/37))

### Improvements

- Dropped the issue and pull request templates from a generated feedstock, so it ships only what recording needs. ([#37](https://github.com/climate-resource/copier-bookshelf-dataset/pull/37))
- Replaced the stock Python `.gitignore` in a generated feedstock with a short one.
  It names only what a feedstock produces: the bundle, the virtual environment, the tool caches and macOS clutter.
  A `copier update` rejection stays visible, so the `forbidden files` hook can still refuse to commit one. ([#43](https://github.com/climate-resource/copier-bookshelf-dataset/pull/43))
- Cut the generated `renovate.json` down to the two rules that keep Renovate away from the Copier owned pins,
  plus the `copier` and `pre-commit` managers.
  Everything else was a preference the file restated, so a feedstock now takes it from `config:best-practices`.
  Lock file maintenance survives the trim, because that preset already runs it early on a Monday.

  Moves the three day soak for new Python releases from Renovate into uv,
  as `exclude-newer` in the generated `pyproject.toml`.
  This applies to every `uv lock` and `uv sync`, not only to Renovate pull requests.
  `bookshelf` is exempt, so a feedstock can pick up a fresh SDK release straight away. ([#44](https://github.com/climate-resource/copier-bookshelf-dataset/pull/44))
- Trimmed the generated `ruff.toml` and `.pre-commit-config.yaml` from 93 lines to 45.
  The ruff config now carries house style only,
  because ruff reads the Python version and the line length from `pyproject.toml`.
  The pre-commit config keeps the hooks that stop a feedstock committing data, keys or Copier rejection files,
  and drops the ones ruff already covers.
  It keeps `check-yaml` and `check-json`, because ruff parses neither,
  and a malformed recipe or Renovate config otherwise fails silently.
  Dropping the per-file ignores changes behaviour rather than only shortening the file:
  a test file a feedstock adds later now has `D`, `S101` and `PLR2004` applied to it,
  where the old config exempted all three.
  Renovate moves the hook revisions, so the pre-commit.ci autoupdate block is gone. ([#45](https://github.com/climate-resource/copier-bookshelf-dataset/pull/45))
- Trimmed the feedstock questions from eight to seven.
  `dataset_name_human` now defaults to `dataset_name` with hyphens replaced and words capitalised.
  Enter is the right answer for a conventional name, and the prompt is still there to fix the casing.
  Stopped asking for the Bookshelf SDK version, because the reusable workflow installs exactly that version.
  It follows the template now, so `copier update` is the only thing that moves the pin. ([#46](https://github.com/climate-resource/copier-bookshelf-dataset/pull/46))
- Trimmed the generated README to the dataset itself: what it is, how to build it and how to change it.
  The platform and CI narrative now lives only in this template's README, which the generated one links to. ([#47](https://github.com/climate-resource/copier-bookshelf-dataset/pull/47))
- Reworked this template's README around the steps to create, publish from and update a feedstock.
  Moved the CI internals and fleet maintenance notes under template development.
  Changed the default Bookshelf API URL to `https://bookshelf.climateresource.com.au`.
  Passed the API URL to the preview upload through `BOOKSHELF_API_URL`.
  Made the bump workflow publish the GitHub release instead of drafting it.
  Renamed the repository variable for the API URL to `BOOKSHELF_API_URL`, matching the SDK. ([#49](https://github.com/climate-resource/copier-bookshelf-dataset/pull/49))
- Raised the scaffolded `bookshelf` pin to 1.0.0b13.
  That release makes production the SDK's default deployment,
  so a scaffolded feedstock reaches the live platform without a deployment override. ([#50](https://github.com/climate-resource/copier-bookshelf-dataset/pull/50))
- Dropped the `dataframes` extra from the scaffolded dependency, because pandas and pyarrow are core to the SDK.
  Stopped writing the production API URL into the workflows, because that is the SDK default from 1.0.0b13.
  Setting the `BOOKSHELF_API_URL` repository variable still selects another deployment. ([#51](https://github.com/climate-resource/copier-bookshelf-dataset/pull/51))

### Improved Documentation

- Documented how a fleet of feedstocks is kept in sync: the topic that finds them, the Renovate copier manager that updates each one, and a mani fan-out for the rest. ([#37](https://github.com/climate-resource/copier-bookshelf-dataset/pull/37))


## copier-bookshelf-dataset v0.4.1 (2026-09-13)

### Bug Fixes

- Found each target's bundle whether its artifact landed in a directory of its own or flat.
  A pull request with one book downloads a single bundle artifact,
  which unpacks into the download path itself, so the preview upload refused to run. ([#36](https://github.com/climate-resource/copier-bookshelf-dataset/pull/36))


## copier-bookshelf-dataset v0.4.0 (2026-09-13)

### Breaking Changes

- Replaced the single `Record and validate bundles` CI job
  with the `candidate`, `targets`, `record` and `candidate outcome` jobs.
  The `bookshelf-bundle` artifact became one `bookshelf-bundle-<volume>-<version>` artifact per book.
  A branch ruleset that requires the old check name has to be updated after moving to this template version. ([#33](https://github.com/climate-resource/copier-bookshelf-dataset/pull/33))
- Made `sdk-version` a required input of the reusable feedstock CI workflow.
  Its `upload preview` job also asks the caller to grant `id-token: write`,
  so a caller that moved to this template version without both failed at startup. ([#34](https://github.com/climate-resource/copier-bookshelf-dataset/pull/34))
- Renamed the generated CI caller's job from `record` to `Bookshelf`,
  so its checks now report as `Bookshelf / ...` instead of `record / ...`.
  A ruleset that required the old check names has to be updated after moving to this template version.
  The generated `pyproject.toml` also pinned `bookshelf` to the exact `bookshelf_sdk_version` answer,
  so a feedstock has to run `uv lock` after `copier update`. ([#35](https://github.com/climate-resource/copier-bookshelf-dataset/pull/35))

### Features

- Changed feedstock CI to validate a pull request as its head merged with the current `main`,
  and to record that candidate's identity.
  Each `(volume, version)` target is now recorded in its own matrix leg with an `outcome.json`,
  and a `candidate outcome` job fails unless every expected book was validated. ([#33](https://github.com/climate-resource/copier-bookshelf-dataset/pull/33))
- Added an `upload preview` job to the reusable feedstock CI workflow.
  It stored the candidate's books on the Bookshelf platform for reviewers,
  authenticating with the run's GitHub Actions OIDC token rather than a credential.
  The workflow gained an optional `api-base-url` input. ([#34](https://github.com/climate-resource/copier-bookshelf-dataset/pull/34))
- Rolled PR preview publication out through the generated CI caller with a shared SDK pin.
  Added an `extra_recipes` answer for more volumes, with a multi-volume regression fixture.
  Documented the repository rules a feedstock needs for PR publication. ([#35](https://github.com/climate-resource/copier-bookshelf-dataset/pull/35))

### Improvements

- Raised the scaffolded `bookshelf` floor to 1.0.0b7. ([#32](https://github.com/climate-resource/copier-bookshelf-dataset/pull/32))

### Improved Documentation

- Documented the `bookshelf-feedstock` GitHub topic in the new-repository steps. ([#25](https://github.com/climate-resource/copier-bookshelf-dataset/pull/25))


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
