# Human handoff

The reusable feedstock workflows and their composite action now live in this public Copier repository.
No separate `bookshelf-actions` repository or sliding `v1` tag is needed.
Release this repository through its existing bump and release process.
A generated feedstock pins the exact Copier tag used to generate it.

## Configure a feedstock

Configure the feedstock repository environment named `deploy` with `BOOKSHELF_CLIENT_ID` and `BOOKSHELF_CLIENT_SECRET` as environment secrets.
Keep `secrets: inherit` in the generated publish caller.
The reusable publish job attaches `environment: deploy`, which makes those environment secrets available to the job.
Set the public `BOOKSHELF_TOKEN_URL` repository variable to the approved WorkOS AuthKit token endpoint.
For staging, set `BOOKSHELF_API_BASE_URL` to the staging Bookshelf API URL.

## Validate a real feedstock

Validate against `climate-resource/bookshelf-primap-hist@poc/platform-migration`, the proof of concept from bookshelf-platform issue 256.

1. Generate a fresh feedstock from a released version of this Copier template.
2. Confirm the generated callers pin that exact template tag.
3. Compare its root `bookshelf.yaml`, `build.py`, dependency extras, Ruff `E402` exception, and workflow callers with the PoC migration files.
4. In the PoC checkout, add the generated files and run `uv lock`.
5. Run feedstock CI and confirm recording and validation are green.
6. Run publish against staging and confirm the summary says `published`.
7. Run publish again and confirm the summary says `no-op` with the same edition.

The intended feedstock dependency is `bookshelf-client[cli,publish,dataframes]>=0.3.1b4`.
That distribution coordinate is not currently available from the configured package index.
Publish the record and replay client at that coordinate, then regenerate and commit each feedstock `uv.lock` before running either reusable workflow.
