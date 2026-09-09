# Bookshelf PR comparison prototype

Throwaway exploration on `prototype/pr-dataset-diff`. No production template or workflow changes.

## Recommendation

Start with an offline report generated from two recorded bundles. Upload the HTML and a machine-readable comparison as GitHub Actions artifacts, and put a short summary in the job summary. This needs no Bookshelf write credentials or report hosting service.

Use the PR base commit as the initial default baseline. Add a separately labelled comparison against a pinned published edition when the question is “what will change for consumers?” Neither baseline answers both questions. This default is a proposal, not a confirmed user preference.

The prototype answers whether metadata and data changes can be explained from bundles alone. They can for supported tables. Hosting is a separate decision. The remaining questions are what baseline reviewers prefer, which table identities need explicit configuration, and what scale the report must handle.

## Try it

Open [demo.html](demo.html) directly. It has seven scenarios, tolerance controls, before/after plots, metadata differences, row membership changes, and exact cell differences.

1. Select **Values and coverage**. Expect two changed cells, one new null and one added region.
2. Set relative tolerance to `0.11`. Exact changes remain two; material changes become one because the new null still counts.
3. Select **Reordered rows**. Byte hashes differ, but row and cell changes are zero.
4. Select **Unit change**. One series is removed and one added. Values with different units are not subtracted.
5. Select **Duplicate identity**, then **Missing baseline**. Each explicitly explains why a comparison cannot be made.

Rebuild the synthetic demo with:

```sh
uv run prototypes/pr-dataset-diff/build.py
```

Generate a report from two real bundle directories, each containing `manifest.lock`:

```sh
uv run prototypes/pr-dataset-diff/build.py \
  --before /path/to/base/bundle/v1.0.0 \
  --after /path/to/head/bundle/v1.0.0 \
  --baseline 'PR base: FULL_BASE_SHA' \
  --candidate 'PR head: FULL_HEAD_SHA' \
  --out /tmp/bookshelf-comparison.html
```

Omit `--before` to demonstrate unavailable-baseline handling. For generic tabular data, supply a resource-to-key mapping, for example `--keys '{"emissions":["region","scenario","unit","year"]}'`. Annual wide timeseries infer identity from every non-year column; check the displayed keys. CSV columns stay text in this prototype, so CSV values have exact textual comparisons rather than numeric tolerances.

The command writes HTML and JSON. Open [viewer.html](viewer.html), then choose the JSON file with **Open comparison JSON**. This is the second prototype: a reusable viewer consuming a local comparison payload. No data is sent anywhere. **Save comparison JSON** exports the selected scenario for the same workflow.

## Options

| Delivery | How it works | Benefits | Cost / limitation |
| --- | --- | --- | --- |
| Self-contained HTML artifact | CI records both sides and embeds the comparison into HTML | Works offline, no service or API writes, simplest first step | Reviewers download and open the artifact; artifacts expire |
| Local JSON in a reusable viewer | CI emits JSON; a reviewer opens it in a Bookshelf frontend route or standalone viewer | Reuses frontend components without storing PR datasets | One manual file selection; a Bookshelf route still needs implementation |
| Static report hosting | Upload generated HTML under repository / PR / commit | Direct clickable PR link; same report generator | Needs storage, URL ownership, retention and access rules; public hosting cannot carry restricted datasets |
| Temporary Bookshelf comparison API | Upload a comparison result, return an authenticated viewer URL | Convenient PR links, central retention and access control | New endpoint and storage lifecycle; no matching endpoint found in inspected checkout |
| Publish candidate books and compare editions | Register candidate data, then query both editions | Could reuse normal browsing and data query components | Publishing changes catalogue state; requires credentials and cleanup; poor default for PR previews |

GitHub documents artifacts as downloadable files for signed-in users with repository read access. Its default retention is 90 days. Uploading HTML as an artifact does not itself supply the browsable report URL that climate-ref's report store provides. See [downloading workflow artifacts](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts).

## What the report should tell a reviewer

Compare book framing, resolved discovery metadata, license, authors, visibility, entries and data dictionaries. Match entries and resources by name. Keep build provenance and writer versions in their own section so a new code reference does not dominate scientific changes.

For each table, report added/removed columns and type changes, added/removed identities, changed cells, null transitions, absolute changes and relative changes. A percentage relative to zero is undefined. Show exact changes even when tolerances suppress numerical noise. Keep units in series identity; unit conversions require explicit rules.

A different content hash is a reason to inspect values, not proof they changed. Parquet writer upgrades or row ordering can change bytes without changing observations. External pointers only support metadata and identity comparison until a separate fetch policy exists. Unknown formats and ambiguous keys must be “not compared”, never green zeroes.

For production, add dimension coverage summaries, time-range changes, largest changes per variable and unit, and filters for region/scenario/variable. Compute complete counts in CI with bounded examples and plot samples in the artifact. The prototype embeds full table inputs to make the comparison logic inspectable; that payload is deliberately unsuitable for large datasets.

## CI shape

1. Capture the PR base SHA and head SHA. Choose explicitly whether candidate means PR head or GitHub's synthetic merge commit; the existing checkout defaults do not make this a reliable head-only comparison. Label both code references in the report. A merge-base comparison could be a separate mode when that better matches the review.
2. Obtain a validated baseline bundle from a successful build of that exact SHA. Reuse an artifact only when its recorded SHA and build inputs match. If it expired, rebuild in an isolated checkout using that commit's lockfile and pinned inputs. A missing or failed baseline must produce an incomplete report, not an empty dataset.
3. Record the candidate in a separate environment with its own locked dependencies. Use the union of versions from both recipes so removed versions are visible. Pair the same `(volume, version)`; a new version is added unless an explicit cross-version baseline is selected.
4. Run the comparator on downloaded bundles with a trusted, pinned report tool. Never give candidate build code publish credentials. The existing reusable workflow/action pinning is a useful pattern here.
5. Upload `index.html`, a comparison result JSON and a short Markdown summary. Write the summary to `GITHUB_STEP_SUMMARY`. Retain both bundle identities and input hashes in the report. Baseline/input availability is part of the result.
6. Optionally add a sticky PR comment linking the workflow artifact. Posting requires a separate permission decision and suitable handling for fork PRs; it is not needed for the first version. Do not run untrusted PR code in a privileged `pull_request_target` job.

For a published baseline, resolve `(volume, version, edition)` once, then download its metadata and resource bytes using read access. Save the edition and hashes so a later publish cannot silently move the baseline. The edition is server-owned and is absent from recorded bundles. A published-state adapter must also preserve editorial corrections made on the server, which may differ from an old feedstock bundle.

For unpinned upstream URLs, rebuilding old code today does not reconstruct the historical input. Preserve original bundles or content-addressed inputs, and expose input changes in either baseline mode.

## Possible API contract, not implemented

If downloading becomes the main source of friction, add a preview-specific service rather than replaying a bundle. CI would upload a versioned comparison result with repository, PR, base/head SHA, baseline kind and pinned edition if applicable, resource hashes, full counts and bounded examples. A proposed `POST /v1/comparisons` could return a comparison ID, viewer URL and expiry.

Keep previews outside catalogue edition creation. Set access to cover the stricter visibility of both inputs, enforce expiry, and bind uploaded results to a verified workflow identity. Large raw datasets need not be posted at all. A read-only frontend route can then render the same comparison result that the standalone HTML embeds.

The prototype JSON uses `schema_version: prototype-1` with `before` and `after` snapshots. It proves local import and a shared comparison model; it does not establish the final production result schema or implement a server.

## Evidence and verification

Inspected local sources on 2026-09-09:

- This template at `831d64b`: `.github/workflows/feedstock-ci.yaml` uploads validated bundles already. `actions/record-bundle/action.yml` records every recipe version without API credentials.
- [Bookshelf bundle specification](https://github.com/climate-resource/bookshelf/blob/ca7fedc80805f60b7747597da34b3cdc7602e0d0/docs/explanation/bundle-format.md): content-addressed resources, book metadata, schema versioning, writer versions and the absence of server edition identifiers.
- [Platform bundle endpoint](https://github.com/climate-resource/bookshelf-platform/blob/03a8edbc2b8ac2743caa3fa62f6820d86abf556d/src/bookshelf_api/api/v1_bundles.py): `/v1/bundles/replay` registers resources and can publish a book. Searched that checkout's API modules, generated frontend services and routes; found no comparison endpoint/viewer. This does not establish what another branch or deployment contains.
- [climate-ref report workflow](https://github.com/Climate-REF/climate-ref/blob/e59d77ccc9eeb7967d57f3af938e17cf09b788c8/.github/workflows/regression-diff-report.yaml): builds a report, uploads to an R2-backed report store, writes a job summary and posts a sticky comment. Its renderer separates analysis from Jinja templates. That separation transfers well; the report host does not exist here.

Executed the bundle reader against the local `bookshelf-test` v0.1.0 bundle. Comparing it with itself produced zero data cell changes. A scratch copy with `2021` changed from `4` to `4.4` and `2022` changed from `6` to null produced two changes and one new null. The reader correctly inspected a declared CSV whose content-addressed filename ended in `.parquet`. An older schema bundle was refused.

Executed the pure JavaScript comparison module for all seven scenarios and parsed both script blocks for syntax. The 11% tolerance experiment retained the null change while suppressing the 10% numeric change. No automated test suite was added to this throwaway prototype.

Browser policy blocked navigation to the local HTML file. Visual layout, browser file import, and download interactions remain unverified. Real local bundles and their reports are kept in `/tmp`, not committed here. Only the explicitly synthetic demo is captured on this branch. No API uploads, CI execution, hosted deployment or PR comments were performed.
