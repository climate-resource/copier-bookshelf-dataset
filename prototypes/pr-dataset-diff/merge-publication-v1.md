# Initial workflow: merge publishes

Selected by the user. Every push produces Bookshelf previews. A required GitHub check blocks merging until every expected book has built, validated and uploaded successfully. One updated PR comment supports human review. Merge publishes the changed books; no GitHub release or separate Bookshelf approval is required.

The [interactive prototype](publication-workflows.html?variant=merge) opens with two books passed, one running and one queued. Try merging, finish both remaining books, then merge again. The required check and review comment update with the same latest-push state.

This document is an implementation contract. The artifact simulates it; production workflows and repository rules have not been changed.

The [research and implementation plan](../../docs/design/pr-publication.md) consolidates the decisions, including building the PR merged with pinned main, and defines the implementation sequence. It is the current source for the complete design. This document supplies the earlier check/comment detail.

## Required check

Proposed stable name: `Bookshelf / validate publication`.

The expected publication set is keyed by `(volume, version)`, with one or more named resources beneath each book. Discover the complete set before running the books. All declared targets must be accounted for, including unchanged books. Multi-volume discovery must not collide on a shared version name.

| Result for the current PR commit | Required check | Merge |
| --- | --- | --- |
| Discovery or any book still queued/running | In progress | Blocked |
| All expected books built, validated and uploaded | Success | Allowed, subject to existing GitHub rules |
| Any failed build, validation or upload | Failure | Blocked |
| Missing results, unexpected target set, cancelled run or execution error | Failure or cancelled | Blocked |
| Earlier commit succeeds after a new push | Earlier check remains historical | Latest push still blocked |

The aggregate check must run even if an upstream job failed. It explicitly requires successful results for every expected target. Never use a skipped aggregate job or treat an absent book result as success. An empty target set needs an explicit supported no-op rule; the initial implementation should fail discovery rather than silently pass.

Configure this check as required in the repository ruleset or branch protection and select its trusted producer where supported. Merely adding a workflow does not enforce merge blocking. GitHub accepts `success`, `skipped` and `neutral` for required checks, which is why the aggregate must explicitly enforce the successful-book condition. Checks must apply to the latest relevant commit. See [GitHub's required-check troubleshooting](https://docs.github.com/en/enterprise-cloud%40latest/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks) and [protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

Build the PR merged with pinned current `origin/main`. Record the PR head, main revision and merged candidate tree. A change to either Git input invalidates current readiness and requires a new build. If a merge queue is enabled, support its validation event too. Publishing must verify the actual merged output against the reviewed content.

## One review comment

Use a stable marker, for example `<!-- bookshelf-publication-preview -->`, to update the same bot-owned comment rather than post on every push. Verify both marker and author when locating it. Include:

- The latest commit, workflow run and aggregate result.
- A stable Bookshelf proposal link and an immutable link to this push's preview.
- One row per volume/version with build/validation status and a diff or failure link.
- The pinned comparison baseline and enough metadata to distinguish new versions from revisions.
- After merge, publication outcomes and links back to published editions.

Publish an initial pending comment, update progress and failures, then update the final outcome. Never let completion of an older run overwrite the current-head summary. Preserve old preview links in Bookshelf history.

Comment delivery supports review; it is not a formal approval gate. If posting fails, expose that failure in the job summary and retry it without misreporting book validation. The required check retains a link to the preview as a fallback.

The Bookshelf platform owns the check and the comment through its GitHub App. Candidate build code uploads previews with a GitHub Actions OIDC token and holds no reporting or catalogue-publishing credential. Fork PRs are out of scope and receive a failed check that says why. GitHub documents [workflow permissions and fork restrictions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).

## Merge publication

On PR merge, the platform publishes every changed target from the sealed preview that passed the check on the merged head. The feedstock ruleset requires branches to be up to date, so the merged content is the validated candidate. The pinned publication baseline is rechecked inside the write. Do not read a mutable “latest preview” pointer and publish whatever it currently names.

Record the source repository, PR, candidate commit, merge commit, content identities and publication outcome per volume/version. Preserve these receipts after preview-byte expiry. An unchanged book keeps its existing edition. Repeated delivery of the merge event must not mint duplicate editions.

The publication job should attempt the complete set and retain per-book outcomes. If publication partially fails, report exactly which books were published and allow an idempotent retry. The current platform's single-bundle replay does not provide a cross-volume transaction; the initial design must not promise atomic publication across all volumes. The prototype's merge action demonstrates the successful outcome only.

Formal data-owner approvals, review dismissal and selective curator publication are deferred. Existing GitHub code review requirements still apply.

## Work remaining in the repositories

| Area | Current evidence | Required change |
| --- | --- | --- |
| Feedstock CI | `actions/record-bundle` records and validates every version in one recipe | Discover all volume/version targets, retain per-book outcomes, upload previews and aggregate results |
| GitHub reporting | No PR preview comment in `.github/workflows/feedstock-ci.yaml` | Add trusted check/comment reporting tied to the latest commit |
| Bookshelf platform | No preview comparison endpoint or page found in the inspected checkout | Store immutable proposal previews and render diffs using existing tables/charts |
| Publish trigger | Generated `feedstock-publish.yaml` runs on published releases or manual dispatch | Publish from verified merge events with exact content and origin receipts |
| Repository policy | Not inspected or changed remotely | Require the aggregate check in the relevant repository rules |

Changing just the release trigger today would not implement the preview workflow. Platform preview support and complete target discovery are dependencies of the selected design.

## Prototype checks

The selected workflow models queued/running/passed/failed books, the aggregate check, a current-push comment, retries, blocked merging and publication after success. State and rendering checks exercise these cases locally. Native browser layout remains unverified because local-file browser navigation was blocked earlier in this session.
