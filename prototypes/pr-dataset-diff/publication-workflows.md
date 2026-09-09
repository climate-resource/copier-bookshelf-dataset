# Pull requests as Bookshelf publication proposals

Open [publication-workflows.html](publication-workflows.html). This is a self-contained, interactive design artifact. It represents a future page inside Bookshelf, not a proposal to host standalone reports in production. It makes no network calls.

The sample repository has four books across two volumes:

| Volume | Version | Change |
| --- | --- | --- |
| primap-hist | v2.6 | Revise an existing book |
| primap-hist | v2.7 | Add a new version |
| scenario-pathways | v1.1 | Revise an existing book |
| scenario-pathways | v1.0 | Rebuild with no change |

Each book has a data file and a metadata file. Select the book, then switch files to inspect values or metadata. All names, commits, PR details and values in this artifact are illustrative.

## Three workflows

**1. Merge publishes.** The author and reviewer work in GitHub. A check and a persistent comment link to the Bookshelf proposal. Every push uploads a preview. Merge publishes all changed, validated books together. This is the shortest path when GitHub approval is sufficient for both code and data review.

**2. Review in Bookshelf.** Data owners inspect and approve each changed book on the Bookshelf page. Those approvals pass a proposed required GitHub check; merge then publishes the set. A push creates a new snapshot and resets the approvals. This makes sense when reviewers need data tools more than code tools.

**3. Curator publishes.** Merge accepts the work and stages the books. A curator chooses which volume/version targets to publish, potentially on different dates. Try merging, deselecting scenario-pathways v1.1, and publishing both primap-hist versions. The page records the partial outcome and keeps the deferred book visible.

The selector updates `?variant=merge`, `?variant=review` or `?variant=curate`, so a layout can be linked and reopened. Switching workflows resets its simulated state.

## What stays the same

A proposal belongs to `(repository, pull-request number)`. It contains targets keyed by `(volume, version)`, and each target contains named files. A repository is not treated as a single volume. Production recipe discovery needs to support that target collection explicitly.

A push uploads an immutable content snapshot. The stable proposal URL follows the latest snapshot, while old review links remain pinned. The page offers comparisons against a pinned published edition, the PR base commit, and the previous push. A new version without a baseline is shown as added data, rather than compared implicitly against some other version.

Preview publication is immediate on every push. Catalogue publication happens on merge or curator action, depending on the workflow. No GitHub release or tag is needed. The proposed UI keeps preview snapshots out of the catalogue's edition numbering; a changed book receives an edition when promoted, while an unchanged book retains its existing edition.

Each published book retains its originating PR, repository, reviewed snapshot, source commit and merge commit. The prototype's **View origin** link shows the return path. The mock GitHub PR includes the forward link back into Bookshelf. Preview-byte expiry should not erase these publication receipts.

## Decisions exposed by the prototype

- Workflows 1 and 2 propose coordinated publication of the whole changed set. Cross-volume atomicity is a requirement to design, not an existing platform capability demonstrated here. Workflow 3 explicitly permits partial publication.
- All workflows block merge while any target fails validation. Workflow 2 additionally needs all current data approvals. A production repository could adopt a different policy, but this artifact chooses one concrete behaviour for comparison.
- Merged output must match reviewed content. A merge conflict resolution or changed input that alters the result needs a new comparison. The prototype assumes equivalence when its merge button is pressed; it does not rebuild anything.
- Published baseline editions must be checked again at promotion time. Another PR publishing first must not let an old proposal silently supersede newer data. Workflow 3 also needs protection against out-of-order staged publications. These concurrency cases are documented requirements rather than simulated operations.
- Removed targets are withdrawn from the proposal, not deleted from Bookshelf. New volumes require an explicit creation policy. Preview access must honour the data's visibility independently of GitHub repository visibility.
- UI approvals represent data sign-off. GitHub branch protection still decides who can merge. Existing frontend tables, charts and resource access should be reused in implementation; the embedded mock chart only makes this workflow artifact self-contained.

I would start with workflow 1 and add workflow 2 where domain review is required. Workflow 3 is useful when publication timing differs across volumes, but it introduces a queue of merged work that someone must maintain. No workflow has been selected for production.

## Checked

Parsed both script blocks and checked that literal element references resolve. Executed the pure model for each workflow: the first two publish three changed books; the third can publish only the two historical versions. A new push clears approvals and retains prior snapshots. A validation failure and closing without merging both prevent publication. The unchanged version retains its existing edition.

Executed the rendering functions with lightweight element stubs for every combination of workflow, book, file and baseline. The partial-publication catalogue and provenance dialog produced the expected content. This checks JavaScript execution, not browser layout or native interaction.

The earlier browser policy block prevents local-file visual verification in this session. Browser layout, file navigation and native dialog interaction are not verified. The artifact uses inline assets and responsive CSS and can be opened directly by the user. No production template, frontend, CI, API or GitHub state was changed.
