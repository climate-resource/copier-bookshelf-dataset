# Copier: Bookshelf Dataset

This is our [copier](https://copier.readthedocs.io/en/stable/#quick-start) template
for generating new feedstocks for the [Bookshelf](https://climate-resource.github.io/bookshelf/).

The template itself lives in `template`.

## Creating a feedstock

Generating the repository only needs `uv`.

1. Generate the repository:

   ```bash
   uvx copier copy https://github.com/climate-resource/copier-bookshelf-dataset.git $path_to_my_new_repo
   ```

   Copier uses the latest tagged release.
   `--vcs-ref` picks another commit or tag, but Renovate cannot follow an untagged ref.

   Copier asks about the dataset, its author and its URL.

2. Run `make initial-setup` inside the new repository.
   This does the `git init`, sets the origin remote, writes `uv.lock` and makes the first commit.
   Recording derives provenance from git, so it needs all three.

3. Push the repository to GitHub and give it the `bookshelf-feedstock` topic:

   ```bash
   gh repo edit climate-resource/$my_new_repo --add-topic bookshelf-feedstock
   ```

   This topic is how we find every feedstock:
   `gh repo list climate-resource --topic bookshelf-feedstock`.

4. Install the Bookshelf GitHub App on the repository and set up the [repository rules](#repository-rules).

5. Create each volume once with `bookshelf volume create`.
   `bookshelf publish` will not create one, so a missing volume fails with `Series 'NAME' not found`.

### What the template scaffolds

A generated feedstock contains an example recipe to start from.
It turns some checked-in example data under `inputs/` into one timeseries resource.
`make run` records and validates it offline, before a line of real code is written.
Remove `inputs/` once the real data is fetched from elsewhere.

The `extra_recipes` answer adds a recipe per extra volume.
For example, `[second-volume]` adds `bookshelf-second-volume.yaml` alongside `bookshelf.yaml`,
and CI records the books in both.

### Worked examples

The SDK's [examples README](https://github.com/climate-resource/bookshelf/blob/main/examples/README.md)
lists the example feedstocks and explains how to use them.
The [recipe format](https://github.com/climate-resource/bookshelf/blob/main/docs/explanation/recipe-format.md)
documents every field a recipe can carry.

## Publishing data

Opening or reopening a pull request, or pushing to its branch, builds and uploads a preview.
The platform posts one pull request comment and updates it as the preview changes.
When the pull request merges, the platform publishes the preview that passed its check.
Closing without merging leaves the preview unpublished.
Pushes to `main`, the weekly schedule and manual dispatch build and validate without uploading previews.

The Bookshelf GitHub App holds the publishing credentials,
so a feedstock needs no publish credential of its own.
Fork pull requests skip preview uploads, because they cannot mint a token for the upstream repository.
CI reads the API URL from the `BOOKSHELF_API_URL` repository variable and falls back to production.

### How the build is locked down

CI merges the pull request head with the current `main` to build the candidate,
and records and validates each `(volume, version)` target in its own job.
Only the `upload preview` job can mint a GitHub Actions OIDC token.
It installs the pinned SDK and this template's helpers without checking out pull request code.

The reusable workflow lives under `.github/workflows`, with its composite action in `actions/record-bundle`.
Generated callers pin it to the Copier ref used to generate the feedstock.

## Repository rules

A feedstock repository must:

1. Have the Bookshelf GitHub App installed with access to the repository.
2. Grant `id-token: write` to the CI workflow, which the generated CI already does.

A GitHub ruleset should also require the platform's check to pass before merging,
and require the pull request branch to be up to date.
The check is expected to be named `Bookshelf / validate publication`,
but confirm this against the first pull request the App reports on.

## Updating a feedstock

Navigate to the feedstock and run `copier update`.
To keep last time's answers without being asked again, run `copier update --defaults`.
Renovate also opens a pull request when `copier-bookshelf-dataset` has releases.

There will likely be merge conflicts, particularly in `pyproject.toml` around versions.
`copier update --conflict inline` puts the diffs inline
(see [the copier docs](https://copier.readthedocs.io/en/stable/updating/)).
The pre-commit config stops you committing conflict markers or `.rej` files.

Conflicts in `uv.lock` can be safely ignored.
Run `uv lock` after updating to regenerate it, which the `uv-lock` pre-commit hook also catches.

## Template development

### Installation

`uv` is expected to be installed globally.
It manages the virtual environment, `copier`, `ctt` and the test dependencies.

```
make virtual-environment
```

This also installs the pre-commit hooks.

### Keeping every feedstock in sync

A feedstock is thin on purpose.
Its CI is a one-line caller into this repository's reusable workflow,
so most template changes need no per-repository edit at all.
Two rules keep that true:

- A reusable workflow's inputs are an interface.
  Add a new input with a default, so a caller pinned to an older ref keeps working.
- Generated callers pin the template ref that generated them, never `main`.

Renovate carries a template release to every feedstock.
Each feedstock's `renovate.json` enables the `copier` manager,
which opens a `copier update` pull request when this template tags a release.
CI on that pull request records every book, so a template change that breaks a feedstock fails there.
Renovate resolves the template through `.copier-answers.yml`,
so `_src_path` must be the full Git URL and `_commit` must be a plain tag.

For a change that cannot wait for Renovate,
we use `mani` from our workspace repository to run commands across every feedstock.

### Releasing

Version bumps and releases run through `.github/workflows/bump.yaml`.
Dispatch the "Bump version" workflow and pick a bump rule.
The work is delegated to the shared `climate-resource/github-actions` bump workflow,
which generates a changelog and then bumps, tags, and makes a GitHub release.

A green test suite proves the render is valid,
not that the rendered feedstock still works against a live Bookshelf.
The regression check for a template release is the pull request publication pilot,
whose steps are written up in
[#30](https://github.com/climate-resource/copier-bookshelf-dataset/issues/30).
It drives a pull request through the `bookshelf-test` feedstock and asks the API what landed.

### Copier template tester (ctt)

We use [copier template tester (ctt)](https://copier-template-tester.kyleking.me/)
to render the template under the answers in `ctt.toml`.
The output is tracked under `tests/regression/ctt`,
so a template change shows up as a diff of the generated repositories,
at the expense of verbose pull requests.

The pre-commit hook runs ctt on every commit, so the fixtures normally update on their own.
`make ctt` runs it by hand.
On a Renovate pull request the `Regenerate fixtures` workflow runs ctt
and pushes the result back to the branch.
That push uses the organisation `PERSONAL_ACCESS_TOKEN` secret,
because a `GITHUB_TOKEN` push would not re-run CI.

### Tests

```bash
make test       # everything, including the slow rendered-feedstock checks
make test-fast  # skip the slow ones
```

`tests/test_rendered.py` renders every `ctt.toml` case from the working tree,
lints it with `ruff`, checks its workflows with `actionlint`,
validates its pre-commit config, parses its `renovate.json`,
and checks the live render against the committed fixture.
It takes a few minutes, which is the price of knowing every render actually works.

The remaining tests are fast checks over the committed fixtures and the scripts in `actions/record-bundle`.
