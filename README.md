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

## Required secrets

Create a [personal access token](https://docs.github.com/en/enterprise-server@3.4/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#about-personal-access-tokens)
that can be used to write to the repository as part of GitHub actions.
It is best to use the fine-grained tokens
and only give the token access to this repository.
The token will need "Contents" permissions, specifically read and write access for "Contents".

If you can't create a token,
your organisation may need to enable personal access token access.
Please ask one of the lead developers.

Once you have your token, add it to a repository secret
(Settings ->Secrets and variables -> Actions -> New repository secret)
called `PERSONAL_ACCESS_TOKEN`.

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
