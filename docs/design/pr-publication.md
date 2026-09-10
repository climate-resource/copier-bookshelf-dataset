# Pull request previews and merge publication

Status: agreed product direction and platform decisions, ready for implementation.
The platform-side decisions are recorded in bookshelf-platform ADR 0019
(https://github.com/climate-resource/bookshelf-platform/issues/619).

## Purpose

Make Bookshelf datasets reviewable through GitHub pull requests.
Each push builds the proposed data and uploads a preview to Bookshelf.
Reviewers inspect metadata and data differences with Bookshelf's tables and charts.
A required GitHub check blocks merging until every expected book succeeds.
Merge publishes the validated content without a GitHub release.

Published books retain links to the PR and preview that produced them.
A single repository can publish several versions across several volumes in one PR.

The prototype establishes the intended user workflow.
It does not implement preview storage, GitHub enforcement or production publication.
See the [interactive workflow study](../../prototypes/pr-dataset-diff/publication-workflows.html)
and the [check and comment contract](../../prototypes/pr-dataset-diff/merge-publication-v1.md).

## Decisions

| Concern | Behaviour |
| --- | --- |
| Candidate code | The PR head merged with a pinned current `origin/main` |
| Freshness | The feedstock ruleset requires branches to be up to date, so a moved main forces a new push |
| Preview updates | Every PR push |
| Publication scope | All declared volume/version targets in the preview |
| Review | GitHub review supported by Bookshelf comparisons and one platform-owned PR comment |
| Merge readiness | A platform-owned required check that is green only when the latest preview is sealed with every declared book valid |
| Publication | The platform publishes from the sealed preview when its GitHub App hears the merge |
| Releases | No GitHub release or tag required |
| Data approvals | No additional Bookshelf approval process in the initial version |
| Publication failure | Per-book receipts, bounded automatic retries that skip completed books, manual retry endpoint |
| Fork PRs | Out of scope. They receive a failed check that says why |

Work starts with one book to prove the complete integration.
Multiple volumes and versions remain part of the initial product scope, not a later redesign.

## Objects and identity

| Object | Identity and purpose |
| --- | --- |
| Proposal | `(repository, pr_number)`. A small platform record with state and close time. Owns the stable review page |
| Candidate | `(head_sha, main_sha, candidate_tree)`. Code identity only |
| Preview | One immutable upload of every book for one candidate. Own id plus `run_id`, so a rerun is a new preview |
| Book target | Volume and version. Contains named resources and book metadata |
| Comparison baseline | The published `(volume, version, edition)` and its content seal, or absent, pinned on the preview per book |
| Publication receipt | Per-book outcome linking a published or unchanged book to the proposal, preview and merge |

A preview is not a Book.
It never mints an edition, never creates a draft and never touches catalogue state.
Uploading a preview mints nothing.
Merging mints a new edition only for a book whose content seal differs from the published edition.
An unchanged book keeps its edition and still gets a receipt with outcome `unchanged`.

Do not key a target only by version or assume that a repository owns exactly one volume.
Discover the expected target set before running it and reject duplicate volume/version targets.

The stable proposal URL follows the latest preview.
Preview URLs never move.
A rerun that produces different content is a different preview even when its Git inputs are identical.
Retain input hashes and writer/environment provenance alongside the source identity.

## Preview lifecycle

1. CI **creates** a preview with the candidate identity and the full target list.
   The required check goes pending.
2. CI **uploads** each book's bundle.
   Bytes land under `preview/{owner_org_id}/{preview_id}/sha256/{hex}`, never under `ingest/`.
   The same file in two previews is stored twice.
3. CI **seals** the preview.
   The check turns green only when every declared book is present and valid.
   An explicit fail call, a missing book or a preview left unsealed for one hour turns it red.

Uploads authenticate with a GitHub Actions OIDC token.
The platform checks that the token's repository, PR number, head SHA and run id match the preview.
Candidate build code holds no other Bookshelf credential.

Access is per book.
A reader sees the books whose volume they can read and no trace of the others.
Preview resources are served only through preview endpoints.

Retention: preview bytes expire 30 days after the proposal closes or 90 days after upload, whichever comes first.
Merged previews expire the same way, because their bytes now live in the catalogue.
Receipts never expire.

## Two different comparisons

| Reviewer question | Before | After |
| --- | --- | --- |
| What will publication change for consumers? | Pinned published Bookshelf edition | Preview |
| What does this PR contribute? | Build of pinned main | Preview |

Version one offers the `published` baseline and `preview:<id>` only.
The `main` baseline is deferred.
Comparing adjacent previews can help review an update,
but a new preview may include changes from main as well as from the PR, so show both source identities.

The baseline is pinned per book when the preview is created and is never re-resolved.
If someone publishes to that volume during review, the comparison goes stale until the next push.
The publication precondition catches that case.

Pair books by volume and version, then resources by name.
A confirmed new version with no published book is an addition.
A baseline that could not be fetched is unavailable, not empty and not a zero-change result.
Never silently compare a new version with a different version.

The comparison page should show:

- Book metadata, discovery fields, authors, license, visibility, membership and data dictionaries.
- Resource additions/removals, schema changes and row/series coverage changes.
- Exact value changes, null transitions, absolute differences and meaningful relative differences.
- Before/after charts and tables with the compared units and row identity visible.
- Build provenance and writer changes separately from scientific and editorial changes.

Match observations by explicit dimensions.
Keep units in series identity unless a supported conversion is explicitly selected.
Duplicate identities block the numeric comparison.
Byte changes alone do not prove that values changed.
Unknown resource types and external pointers must report what was and was not compared.

Reuse Bookshelf's existing explorer components.
Calculate full counts outside the browser and return bounded examples or paginated results for large datasets.
The earlier standalone HTML experiment is a design reference, not the production delivery mechanism.

## Required check and review comment

The platform owns both, through its GitHub App.
CI builds and uploads. It never holds a comment or check token.

The check is one stable aggregate, provisionally `Bookshelf / validate publication`.
It is bound to the preview's head SHA.
A late completion of an older preview never updates the check on a newer head.
Failure, cancellation, missing results or a mismatched target set must not produce success.
The check must be required by the feedstock ruleset.
Adding a workflow does not enforce merge blocking.

The platform maintains one comment per PR.
It updates on create, seal and failure with the candidate identities, aggregate result, baseline,
per-book status, diff or failure links and the stable proposal link.
After merge it adds publication outcomes.
Older preview links stay available for historical review.
The comment supports review and is not a separate approval gate.
The check's details link points at the proposal page, so review survives a failed comment update.

## Publication and concurrency

When the App hears the merge, the platform queues a publication job for the sealed preview
that passed the check on the merged head.
Publication consumes that preview's bytes and pin.
It never resolves a mutable latest-preview pointer.

The platform does not verify the merged tree.
The feedstock ruleset requires branches to be up to date, so the merged content is the validated candidate.

The publication precondition is enforced inside the write.
For each book the next edition must equal the pinned edition plus one, or one when the pin is absent.
The volume row is locked for the write.
The check runs after the content seal short-circuit, so a retry of a completed book returns its receipt
instead of failing on the baseline it advanced itself.
On a stale pin the book fails, the proposal page and comment say so, and a new push refreshes the comparison.

Publication attempts the full target set and records each result.
It does not promise a transaction spanning multiple volumes.
The job retries a bounded number of times, skipping books that already hold a receipt.
An operator can call the publish endpoint by hand for remaining work.
Duplicate merge deliveries are idempotent on `(proposal, merge_sha)`.

The receipt stores repository, PR number and link, head SHA, main SHA, candidate tree, merge SHA,
preview id, resource hashes and outcome.
`preview_id` is stored by value so receipts outlive previews.
Readers can navigate from a published book to the review that produced it.

Closing a PR without merging marks the proposal closed and publishes nothing.
Removing a target from a later preview withdraws that target. It does not delete a published book.
Publication is driven by merged PRs only.
Direct main pushes, tags and unassociated events must not become alternate publication paths.

## Implementation sequence

### 1. Platform foundations

Record ADR 0019.
Add the proposals, previews and receipts tables, preview storage and the preview endpoints.
Add the GitHub App with OIDC verification, the check run and the comment.
Add the replay precondition and the publication job.

### 2. Prove one book end to end

Use a pilot feedstock and one volume/version.
Build the merged candidate, create, upload and seal a preview, render metadata and data differences,
watch the check and comment update, then merge and confirm the published book carries its receipt.
Exercise a real failing build and a successful retry.
Use the collection-shaped target model from the start.

Done when a reviewer can follow PR to preview to green check to merge to published book to source PR
without a GitHub release.

### 3. Complete multi-book and multi-volume support

Discover all targets, preserve their individual outcomes, aggregate readiness and publish the complete changed set.
Include a new version, an unchanged book and a failed target.

Done when no missing or failed target can hide behind an aggregate success,
and partial publication can be retried without duplicating completed outcomes.

### 4. Verify races, lifecycle and scale

Exercise PR updates, concurrent publication, late CI completion, duplicate webhooks,
closure, preview timeout and preview expiry.
Add representative large-dataset comparison checks and verify access against each supported visibility level.

### 5. Roll out through the template

Ship the reusable workflow changes and generated callers, update Copier regression fixtures,
document the required ruleset and the OIDC setup, and run a pilot against the intended platform deployment.
Remove the release trigger deliberately so both paths cannot publish independently by accident.

## Acceptance criteria

- Every preview identifies its PR head, pinned main revision and merged candidate tree.
- A new push invalidates readiness until a replacement preview seals.
- Reviewers can distinguish publication impact from changes attributable to the PR.
- Every declared volume/version has an explicit outcome. No failed or missing book yields a green check.
- One comment tracks the current preview, while older previews remain addressable.
- Merging is blocked by the required check and needs no additional Bookshelf data approval.
- Publication enforces the pinned baseline inside the write before changing catalogue state.
- Duplicate webhooks and retries do not create duplicate editions or erase partial outcomes.
- Published books retain navigable PR and preview provenance after preview expiry.
- A closed, unmerged PR publishes nothing. Withdrawn targets do not delete catalogue entries.
- Multiple versions and volumes work through the same path as the one-book pilot.

## Deferred

- Fork PRs and a trusted rebuild path for them.
- Verifying the merged tree against the candidate tree, and rebuilding on mismatch.
- The `main` comparison baseline and per-book preview dedupe.
- Formal per-book data approvals, curator-controlled selective publication and cross-volume atomic publication.
- Implicit unit conversion and automatic deletion of published datasets.

A preview for a volume that does not exist is rejected, matching replay.

No production implementation or repository enforcement has been enabled by this write-up.
