# PR publication pilot

Issue #30 uses this checklist to verify the generated caller against the live platform.
Use a pilot feedstock with a branch in the same repository, because fork previews are unsupported.
Record the repository, template ref, SDK version, pull request URLs and workflow run URLs as pilot evidence.

## Repository checklist

- [ ] Install the Bookshelf GitHub App with access to the pilot repository.
- [ ] Require `Bookshelf / validate publication` in the ruleset protecting `main`.
- [ ] Require branches to be up to date before merging.
- [ ] Confirm the CI caller grants only `contents: read` and `id-token: write`.
- [ ] Disable the legacy `Feedstock publish` workflow before enabling PR publication.
- [ ] Update the feedstock to the pilot template ref with `copier update`, then run `uv lock`.
- [ ] Commit the updated caller, answers and lock file.
- [ ] Confirm every recipe volume exists, creating it once with `uv run bookshelf volume create` if needed.

The release trigger remains in the template until #31 removes it.
Both publication paths must not be enabled on the same repository.
The PR caller needs no secrets, environment, token URL, comment step or withdrawal step.
The platform owns the check, comment, merge publication and closure handling.

## Pilot steps

1. Open a pull request that changes the pilot feedstock's data or build output.
   For the multi-volume pilot, include a second recipe and confirm both appear in the caller input.
   Record the head SHA and the current `main` SHA.
2. Watch CI build the merged candidate and upload its preview.
   Check the candidate identity and the outcome for every volume and version in the workflow artifacts.
   Confirm the platform creates `Bookshelf / validate publication` and posts one comment with preview links.
   Open those links and inspect the proposed books.
3. Push a deliberate build failure to the same pull request.
   Confirm CI fails, the required check blocks merging and no publication occurs.
   A missing bundle can leave the platform check expected, which must still block merging.
   Check that the platform has not added a duplicate comment.
4. Fix the build and push again, then retry the successful workflow once.
   Confirm the current candidate passes and the platform updates the same comment.
   Confirm the retry does not publish a book or create a duplicate comment.
   If `main` advances, confirm merging stays blocked until the updated branch passes again.
5. Merge the pull request after the required check passes.
   Watch the platform publish the approved candidate without publishing a GitHub release.
6. Verify every expected book on the platform and inspect its origin.
   Confirm the origin identifies the pilot repository and merged pull request.
   Match the candidate identity and preview to the published books in every volume.
   Save the origin response or page and the published book links with the pilot evidence.
7. Open another pull request, wait for its preview and close it without merging.
   Confirm the platform handles closure and the preview's books are not published.
   Confirm the caller needed no close trigger or withdrawal step.

Stop the pilot if any of these happen:

- A required rule is missing.
- A failing candidate can merge.
- The comment duplicates.
- Publication or origin evidence does not match the approved candidate.

Record the failed step and its run URL for #30 before attempting a wider rollout.
