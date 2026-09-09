# Pull request previews and merge publication

Status: agreed initial product direction; ready for technical research and implementation.

## Purpose

Make Bookshelf datasets reviewable through GitHub pull requests. Each push builds the proposed data and uploads a preview to Bookshelf. Reviewers inspect metadata and data differences with Bookshelf's tables and charts. A required GitHub check blocks merging until every expected book succeeds. Merge publishes the validated content without requiring a GitHub release.

Published books retain links to the PR and build that produced them. A single repository can publish several versions across several volumes in one PR.

The prototype establishes the intended user workflow. It does not implement preview storage, GitHub enforcement or production publication. See the [interactive workflow study](../../prototypes/pr-dataset-diff/publication-workflows.html) and the [check and comment contract](../../prototypes/pr-dataset-diff/merge-publication-v1.md).

## Decisions

| Concern | Initial behaviour |
| --- | --- |
| Candidate code | The PR merged with a pinned current `origin/main` |
| Preview updates | Every PR push, and whenever the relevant main revision changes |
| Publication scope | All declared volume/version targets in the proposal |
| Review | GitHub review supported by Bookshelf comparisons and one updated PR comment |
| Merge readiness | Every expected book builds, validates and uploads successfully for the current candidate |
| Publication | On verified PR merge, using the validated content |
| Releases | No GitHub release or tag required |
| Data approvals | No additional Bookshelf approval process in the initial version |
| Publication failure | Record per-book outcomes and support idempotent retry |

Work starts with one book to prove the complete integration. Multiple volumes and versions remain part of the initial product scope, not a later redesign.

## Objects and identity

| Object | Identity and purpose |
| --- | --- |
| Proposal | Repository identity and PR number; owns the stable review page |
| Candidate | Pinned PR head SHA, main SHA and resulting merged tree; identifies the code being validated |
| Snapshot | An immutable preview with its own ID, candidate identity, run identity and content hashes |
| Book target | Volume and version; contains named resources and book metadata |
| Comparison baseline | Explicit code/build identity or published volume/version/edition, with content identities |
| Publication receipt | Per-book outcome linking published state to the proposal, snapshot and merge |

Do not key a target only by version or assume that a repository owns exactly one volume. Discover the expected target set before running it and reject duplicate volume/version targets.

The stable proposal URL follows the latest candidate. Snapshot URLs never move. A retry that produces different content must create a different snapshot even if its Git inputs are identical. Retain input hashes and writer/environment provenance alongside the source identity.

## Build the intended merged state

Pin the PR head and current main commit, then build their merged result. Record the resulting Git tree and whichever commit identifies the CI candidate. An unresolved merge conflict blocks readiness.

Success applies to those exact inputs. If the PR head or main moves, the old result remains historical and the current proposal becomes pending until its replacement completes. This requires a mechanism to invalidate and rerun candidates when main changes; a PR-push trigger alone is insufficient.

A merge queue is a candidate implementation for this rule. Without one, use an up-to-date-branch policy and rebuild against the new main revision. Research must verify the chosen event and check behaviour for supported GitHub merge strategies, including squash and rebase.

After merge, verify that the actual merged tree matches the validated candidate. Commit SHAs alone are insufficient because GitHub may create a different commit for equivalent merged content. Publish the recorded validated bundles when the identities match. If the merged output differs, rebuild, compare and validate it before publication. The publication job stays blocked while this is unresolved; the PR may already be merged.

## Two different comparisons

| Reviewer question | Before | After |
| --- | --- | --- |
| What will publication change for consumers? | Pinned published Bookshelf edition | Merged candidate |
| What does this PR contribute? | Build of pinned main | Merged candidate |

Use the publication comparison as the default and label the baseline explicitly. Comparing main to the candidate is a separate view. Comparing adjacent preview snapshots can help review an update, but a new snapshot may include changes from main as well as from the PR; show both source identities.

Pair books by volume and version, then resources by name. A confirmed new version with no published book is an addition. A baseline that could not be fetched is unavailable, not empty and not a zero-change result. Never silently compare a new version with a different version.

The comparison page should show:

- Book metadata, discovery fields, authors, license, visibility, membership and data dictionaries.
- Resource additions/removals, schema changes and row/series coverage changes.
- Exact value changes, null transitions, absolute differences and meaningful relative differences.
- Before/after charts and tables with the compared units and row identity visible.
- Build provenance and writer changes separately from scientific and editorial changes.

Match observations by explicit dimensions. Keep units in series identity unless a supported conversion is explicitly selected. Duplicate identities block the numeric comparison. Byte changes alone do not prove that values changed. Unknown resource types and external pointers must report what was and was not compared.

Reuse Bookshelf's existing explorer components. Calculate full counts outside the browser and return bounded examples or paginated results for large datasets. The earlier standalone HTML experiment is a design reference, not the production delivery mechanism.

## Required check and review comment

Use one stable aggregate check, provisionally `Bookshelf / validate publication`. It remains pending while targets run and succeeds only after every expected book has built, validated and uploaded its preview. Include unchanged books in validation. Failure, cancellation, missing results or a mismatched target set must not produce success.

The check must actually be required by repository policy. An always-evaluated aggregate must explicitly inspect all target outcomes, rather than inherit success from skipped jobs. Bind its result to the validated candidate and prevent late completion of an older run from updating current readiness.

Maintain one bot-owned comment per PR. Update it on pushes and completion with the candidate identities, aggregate result, baseline, per-book status, diff/failure links and stable proposal link. Add publication outcomes after merge. Keep immutable snapshot links available for historical review.

The comment supports review and is not a separate approval gate. If comment delivery fails, report that error and retry it. Preserve access through the check's details link and job summary. Existing GitHub review requirements still apply.

Build untrusted candidate code separately from trusted preview/reporting and publication operations. Research the available identity mechanism and fork PR path. Candidate builds must not receive catalogue-publishing or PR-comment credentials.

## Publication and concurrency

Publication consumes a specific validated snapshot and its expected target set. It must not resolve a mutable latest-preview pointer at execution time.

There are two independent freshness checks:

1. The merged Git content must match the validated candidate.
2. The published baseline for each target must still match the edition and content used in its publication comparison.

Another PR can publish between validation and promotion, even when the source trees are valid. Enforce the baseline precondition as part of the publication mutation, with an atomic comparison, lock or equivalent server-side guarantee. A separate read followed by an unchecked write leaves the race open. On mismatch, refresh the comparison and validation before allowing publication. For a new book, the precondition is that the expected published book is still absent.

Retries of a completed target reuse its publication receipt. They must not fail simply because that target's baseline was advanced by the same operation. Already-published outcomes and genuinely stale remaining targets need different handling.

Attempt the full changed set and record each result. Do not promise a transaction spanning multiple volumes. If a later target fails, show the completed and failed targets, mark the publication incomplete, and allow a retry of remaining work without duplicate editions. An unchanged book retains its edition according to Bookshelf's existing content/publication rules; metadata edits remain visible in the report even when they do not create an edition.

Store repository, PR number/link, PR head SHA, pinned main SHA, candidate tree, actual merge identity, snapshot ID, resource hashes and publication outcome in the receipt. Readers should be able to navigate from a published book to the review that produced it. Keep the receipt after preview data expires.

Closing a PR without merging withdraws its previews and publishes nothing. Removing a target from a later proposal withdraws that target; it does not delete a published book. Publication is driven by verified merged PRs in the initial workflow. Direct main pushes, tags and unassociated events must not silently become alternate publication paths.

## Research before implementation choices

The user workflow is sufficiently defined. The following questions concern how to implement it, not whether to change that workflow.

| Area | Question to resolve | Expected result |
| --- | --- | --- |
| Preview storage | How can existing upload/resource storage hold candidate bundles without publishing catalogue editions? | Snapshot model, upload/read contract and access rules |
| Existing frontend | Which explorer, table, chart and metadata components can render two resources? | Comparison-page plan and any missing data-query operations |
| Retention and access | How are previews scoped to dataset visibility and removed after closure/expiry? | Retention policy that preserves publication receipts |
| Target discovery | How should one repository declare multiple volumes and versions? | Repository/recipe contract, collision rules and bundle layout |
| GitHub integration | Which candidate/check events enforce freshness when main moves? How are forks and merge queues handled? | Event flow, trusted identity and required-check configuration |
| Publication | Can existing replay accept expected-baseline preconditions and persist origin receipts? | Safe promotion/retry contract and migration needs |
| Reproducibility | How are upstream bytes, locked dependencies and writer versions retained? | Evidence sufficient to compare or rebuild a pinned candidate |

Inspection so far found offline recording and validation in this template, release-triggered publishing in generated feedstocks, and a single-bundle replay API in the platform. No preview comparison endpoint/page was found in the inspected platform checkout. Reconfirm these findings against the working revisions before implementation.

## Implementation sequence

### 1. Research and agree the technical contracts

Trace recording, upload, resource access, replay and explorer rendering across `bookshelf`, `bookshelf-platform` and this template. Record the request/response shapes, identity fields, permission boundaries and GitHub freshness mechanism. Identify what can be reused before adding new endpoints or storage.

Done when the first end-to-end implementation can be planned against concrete interfaces, including safe handling of a moved main branch and publication baseline.

### 2. Prove one book end to end

Use a pilot feedstock and one volume/version. Build the merged candidate, store its preview, render metadata and data differences, expose the required check and review comment, then publish after a verified merge with an origin receipt. Exercise a real failing build and a successful retry. Use the collection-shaped target model from the start.

Done when a reviewer can follow PR → preview → successful check → merge → published book → source PR without a GitHub release.

### 3. Complete multi-book and multi-volume support

Discover all targets, preserve their individual outcomes, aggregate readiness and publish the complete changed set. Show several versions of the same volume and several volumes from the same repository. Include a new version, an unchanged book and a failed target.

Done when no missing or failed target can be hidden behind an aggregate success, and partial publication can be retried without duplicating completed outcomes.

### 4. Verify races, lifecycle and scale

Exercise PR updates, main movement, concurrent publication, late CI completion, duplicate events, merge-content mismatch, closure and preview expiry. Add representative large-dataset comparison checks and verify access against each supported visibility level. Correctness requirements apply from the first slice; this step broadens evidence before rollout.

### 5. Roll out through the template

Ship the reusable workflow/action changes and generated callers, update Copier regression fixtures, document required repository rules and credentials, and run a pilot against the intended platform deployment. Configure enforcement before enabling automatic publication for a feedstock. Migrate the release trigger deliberately so both paths cannot publish independently by accident.

## Acceptance criteria

- Every current proposal identifies both its PR head and pinned main revision, plus the merged candidate tree.
- A change to either Git input invalidates readiness until a replacement candidate succeeds.
- Reviewers can distinguish publication impact from changes attributable to the PR.
- Every declared volume/version has an explicit outcome; no failed or missing book can yield a green aggregate.
- One comment tracks the current candidate, while older snapshots remain addressable.
- Merging is blocked by the required check and needs no additional Bookshelf data approval.
- Publication verifies merged content and expected published baselines before changing catalogue state.
- Duplicate events and retries do not create duplicate editions or erase partial outcomes.
- Published books retain navigable PR and snapshot provenance after preview expiry.
- A closed, unmerged PR publishes nothing; withdrawn targets do not delete catalogue entries.
- Multiple versions and volumes work through the same path as the one-book pilot.

## Deferred

Formal per-book data approvals, curator-controlled selective publication, cross-volume atomic publication, implicit unit conversion and automatic deletion of published datasets are outside this initial workflow. The retained alternative prototypes document possible later directions.

No production implementation or repository enforcement has been enabled by this write-up.
