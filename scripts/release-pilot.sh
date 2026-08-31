#!/usr/bin/env bash
# Pilot a template release end to end against a real feedstock.
#
# Takes a tagged release of this template, updates the pilot feedstock onto it,
# records the book locally, bumps and tags the feedstock, publishes the draft
# release, follows the publish workflow, and asks the API what landed.
#
# State carries between invocations, so a run that stops half way resumes with
# --from rather than starting over.
#
# Usage: bash scripts/release-pilot.sh --template-ref v0.3.0

set -euo pipefail

STEPS=(preflight update record push bump release publish verify)

TEMPLATE_REF=""
FEEDSTOCK="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/bookshelf-test"
BUMP_RULE="patch"
API_URL=""
DATASET_VERSION=""
FROM_STEP="preflight"
TO_STEP="verify"
ASSUME_YES="false"
TRUST="false"
ALLOW_UNCHANGED="false"

usage() {
    sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    cat <<'EOF'

Options:
  --template-ref TAG     Template tag to pilot. Defaults to the latest release of this repository.
  --feedstock PATH       Feedstock clone to pilot with. Defaults to ../bookshelf-test.
  --dataset-version VER  Book version to record locally. Defaults to the last entry in the recipe.
  --bump-rule RULE       Rule passed to the feedstock's Bump version workflow. Defaults to patch.
  --api-url URL          Deployment the verify step reads. The publish workflow targets the
                         feedstock's own BOOKSHELF_API_BASE_URL, so pointing this elsewhere
                         verifies a deployment the pilot did not publish to.
  --from STEP            First step to run. One of: preflight update record push bump release publish verify.
  --to STEP              Last step to run.
  --yes                  Do not prompt before pushing or publishing the release.
  --trust                Pass --trust to copier. Needed when the feedstock was generated from a
                         template version that declared tasks. Read them before trusting them.
  --allow-unchanged      Pass the verify step when the book did not move. Publishing an unchanged
                         book is idempotent, so a release that changes nothing it records lands no
                         new edition. Without this, no new edition is a failure.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --template-ref) TEMPLATE_REF="$2"; shift 2 ;;
        --feedstock) FEEDSTOCK="$2"; shift 2 ;;
        --dataset-version) DATASET_VERSION="$2"; shift 2 ;;
        --bump-rule) BUMP_RULE="$2"; shift 2 ;;
        --api-url) API_URL="$2"; shift 2 ;;
        --from) FROM_STEP="$2"; shift 2 ;;
        --to) TO_STEP="$2"; shift 2 ;;
        --yes) ASSUME_YES="true"; shift ;;
        --trust) TRUST="true"; shift ;;
        --allow-unchanged) ALLOW_UNCHANGED="true"; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

say() { printf '\n=== %s ===\n' "$*"; }
note() { printf '    %s\n' "$@"; }

# Each argument after the first is one indented continuation line.
die() {
    printf '\nrelease-pilot: %s\n' "$1" >&2
    shift
    for line in "$@"; do
        printf '    %s\n' "${line}" >&2
    done
    exit 1
}

confirm() {
    [[ "${ASSUME_YES}" == "true" ]] && return 0
    read -r -p "$1 [y/N] " reply
    [[ "${reply}" == "y" || "${reply}" == "Y" ]] || die "stopped at the prompt"
}

step_index() {
    local wanted="$1" i=0
    for step in "${STEPS[@]}"; do
        [[ "${step}" == "${wanted}" ]] && { echo "${i}"; return 0; }
        i=$((i + 1))
    done
    die "unknown step: ${wanted}"
}

FROM_INDEX="$(step_index "${FROM_STEP}")"
TO_INDEX="$(step_index "${TO_STEP}")"
[[ "${FROM_INDEX}" -le "${TO_INDEX}" ]] || die "--from ${FROM_STEP} comes after --to ${TO_STEP}"

wants() {
    local index
    index="$(step_index "$1")"
    [[ "${index}" -ge "${FROM_INDEX}" && "${index}" -le "${TO_INDEX}" ]]
}

# The feedstock's own venv holds the bookshelf CLI, so every call runs from there.
feedstock() { (cd "${FEEDSTOCK}" && "$@"); }

API_ARGS=()
if [[ -n "${API_URL}" ]]; then
    API_ARGS=(--api-url "${API_URL}")
fi

[[ -d "${FEEDSTOCK}/.git" ]] || die "no git repository at ${FEEDSTOCK}. Pass --feedstock PATH."

# A resumed run reads what the run before it left, so the state outlives one invocation.
# Everything in it is derived, so deleting the file only costs a full run.
SLUG="$(feedstock git remote get-url origin | sed -e 's#\.git$##' -e 's#.*[:/]\([^/]*\)/\([^/]*\)$#\1-\2#')"
STATE_FILE="${XDG_STATE_HOME:-${HOME}/.local/state}/release-pilot/${SLUG}.env"
mkdir -p "$(dirname "${STATE_FILE}")"
touch "${STATE_FILE}"

state_get() {
    sed -n "s/^$1=//p" "${STATE_FILE}" | tail -1
}

state_put() {
    [[ "$2" != *$'\n'* ]] || die "release-pilot state holds one line per key, and $1 is not one"
    state_drop "$1"
    printf '%s=%s\n' "$1" "$2" >>"${STATE_FILE}"
}

state_drop() {
    local rest
    rest="$(grep -v "^$1=" "${STATE_FILE}" || true)"
    printf '%s\n' "${rest}" | sed '/^$/d' >"${STATE_FILE}"
}

is_number() {
    [[ "$1" =~ ^[0-9]+$ ]]
}

recipe_value() {
    # Reads one value out of the recipe. The pre-volume format is still read, because
    # preflight runs before the update that moves a feedstock onto the current one.
    feedstock uv run --with pyyaml python - "$1" <<'PY'
import sys, yaml

with open("bookshelf.yaml") as handle:
    document = yaml.safe_load(handle) or {}
if sys.argv[1] == "volume":
    volume = document.get("volume")
    name = volume.get("name") if isinstance(volume, dict) else None
    print(name or document.get("collection") or "")
else:
    books = document.get("books") or []
    print(books[-1]["version"] if books else "")
PY
}

latest_run_id() {
    # Newest run of one workflow, or 0 when the workflow has never run.
    feedstock gh run list --workflow "$1" --limit 1 --json databaseId \
        --jq '.[0].databaseId // 0'
}

draft_releases() {
    feedstock gh release list --limit 100 --json tagName,isDraft "$@"
}

draft_tags() {
    # Wrapped in the delimiter, so an empty list still reads as a value that was recorded.
    draft_releases --jq 'map(select(.isDraft)) | map(.tagName) | ",\(join(",")),"'
}

watch_new_run() {
    # Waits for a run of $1 newer than $2 to appear, then follows it to its exit code.
    local workflow="$1" baseline="$2" waited=0 run_id
    is_number "${baseline}" && [[ "${baseline}" -gt 0 ]] \
        || die "no baseline recorded for ${workflow}, so a finished earlier run would pass as this one." \
            "Re-run the step that dispatches it."
    while :; do
        run_id="$(latest_run_id "${workflow}")"
        [[ "${run_id}" -gt "${baseline}" ]] && break
        [[ "${waited}" -ge 180 ]] && die "no new ${workflow} run appeared within three minutes"
        sleep 5
        waited=$((waited + 5))
    done
    note "watching run ${run_id}"
    feedstock gh run watch "${run_id}" --exit-status \
        || die "${workflow} run ${run_id} failed. See: gh run view ${run_id} --log-failed"
}

editions_now() {
    # Exit 5 is the volume not being there yet, which is a count of zero rather than a failure.
    # Anything else is refused, so a credential that reads nothing cannot pass as an empty volume.
    local document="${WORK}/volume.json" code=0
    feedstock uv run bookshelf show "${VOLUME}" --json "${API_ARGS[@]}" \
        >"${document}" 2>"${WORK}/volume.err" || code=$?
    case "${code}" in
        0) jq '[.versions[]?.editions[]?] | length' "${document}" ;;
        5) echo 0 ;;
        *) die "cannot read ${VOLUME} from the API, bookshelf exited ${code}." \
            "$(tail -1 "${WORK}/volume.err")" ;;
    esac
}

resolve_template_ref() {
    [[ -n "${TEMPLATE_REF}" ]] && return 0
    TEMPLATE_REF="$(gh release view --repo climate-resource/copier-bookshelf-dataset \
        --json tagName --jq .tagName)"
    note "no --template-ref given, using the latest release"
}

VOLUME=""

resolve_recipe() {
    # Reads the volume and the book version out of the recipe, once.
    [[ -n "${VOLUME}" ]] && return 0
    VOLUME="$(recipe_value volume)"
    [[ -n "${VOLUME}" ]] || die "cannot read the volume name out of ${FEEDSTOCK}/bookshelf.yaml"
    [[ -n "${DATASET_VERSION}" ]] || DATASET_VERSION="$(recipe_value version)"
    [[ -n "${DATASET_VERSION}" ]] \
        || die "cannot read a book version out of the recipe. Pass --dataset-version."
}

if wants preflight; then
    say "Preflight"
    for tool in gh jq uv git; do
        command -v "${tool}" >/dev/null || die "${tool} is not on PATH"
    done
    gh auth status >/dev/null 2>&1 || die "gh is not authenticated. Run: gh auth login"
    # A stored credential that cannot refresh drops the client to anonymous without saying so,
    # which would read a hidden volume as an empty one and give the verify step a false baseline.
    feedstock uv run bookshelf auth whoami >/dev/null 2>&1 \
        || die "the Bookshelf credential is missing or expired," \
            "so the pilot could not tell an empty volume from one it cannot see." \
            "Run: (cd ${FEEDSTOCK} && uv run bookshelf auth login)"

    [[ -z "$(feedstock git status --porcelain)" ]] \
        || die "${FEEDSTOCK} has uncommitted changes. Commit or stash them first."
    branch="$(feedstock git rev-parse --abbrev-ref HEAD)"
    [[ "${branch}" == "main" ]] || die "${FEEDSTOCK} is on ${branch}, not main"
    feedstock git fetch --quiet --tags origin
    [[ "$(feedstock git rev-parse HEAD)" == "$(feedstock git rev-parse origin/main)" ]] \
        || die "${FEEDSTOCK} is not level with origin/main"

    resolve_template_ref
    gh api "repos/climate-resource/copier-bookshelf-dataset/git/ref/tags/${TEMPLATE_REF}" \
        >/dev/null 2>&1 || die "${TEMPLATE_REF} is not a tag on the template repository"

    resolve_recipe
    # Taken before anything is released, so the verify step can prove the book moved.
    state_put before_editions "$(editions_now)"
    note "template ref:   ${TEMPLATE_REF}"
    note "feedstock:      ${FEEDSTOCK}"
    note "publish target: $(feedstock gh repo view --json nameWithOwner --jq .nameWithOwner)"
    note "the API holds $(state_get before_editions) edition(s) of ${VOLUME} today"
fi

resolve_template_ref

if wants update; then
    say "Update the feedstock onto ${TEMPLATE_REF}"
    copier_args=(--vcs-ref "${TEMPLATE_REF}" --defaults --conflict inline)
    [[ "${TRUST}" == "true" ]] && copier_args+=(--trust)
    feedstock uvx copier update "${copier_args[@]}" || die "copier update failed (exit $?)." \
        "Exit 4 means the template version this feedstock was generated from declares tasks." \
        "Copier replays that old version during an update, so it asks for consent." \
        "Read the tasks on that ref, then re-run with --trust."
    markers="$(feedstock git grep -lI -e '<<<<<<<' -e '>>>>>>>' -- . 2>/dev/null || true)"
    if [[ -n "${markers}" ]]; then
        printf '%s\n' "${markers}"
        die "the update left conflict markers. Resolve them, then re-run with --from record."
    fi
    feedstock uv lock
    feedstock uv sync
    feedstock git --no-pager diff --stat
fi

if wants record; then
    resolve_recipe
    say "Record ${VOLUME}@${DATASET_VERSION} locally"
    # A first publish into a new volume is refused, so say so before anything is released.
    feedstock uv run bookshelf show "${VOLUME}" "${API_ARGS[@]}" >/dev/null 2>&1 \
        || note "warning: no volume named ${VOLUME} that this credential can see." \
            "A first publish needs it created once with 'bookshelf volume create'."
    # Proves the rendered feedstock still builds before anything reaches CI.
    feedstock make run "VERSION=${DATASET_VERSION}"
fi

if wants push; then
    say "Commit and push the update"
    if [[ -n "$(feedstock git status --porcelain)" ]]; then
        confirm "Push the template update to origin/main?"
        feedstock git add -A
        feedstock git commit -q -m "chore: update from copier-bookshelf-dataset ${TEMPLATE_REF}"
        feedstock git push origin main
    else
        note "nothing to commit, the update changed nothing"
    fi
fi

if wants bump; then
    say "Bump the feedstock version"
    # Both baselines are taken before the dispatch, so neither a finished earlier run nor a
    # leftover draft from a previous pilot can be mistaken for this one's.
    drafts="$(draft_tags)"
    baseline="$(latest_run_id bump.yaml)"
    state_put drafts_before "${drafts}"
    feedstock gh workflow run bump.yaml -f "bump_rule=${BUMP_RULE}"
    watch_new_run bump.yaml "${baseline}"
    feedstock git fetch --quiet --tags origin
fi

if wants release; then
    say "Publish the draft release"
    before="$(state_get drafts_before)"
    [[ -n "${before}" ]] \
        || die "no draft release baseline was recorded," \
            "so a leftover draft from an earlier pilot would be published instead." \
            "Re-run the bump step."
    RELEASE_TAG="$(draft_releases \
        | jq -r --arg before "${before}" \
            '[.[] | select(.isDraft) | .tagName | select(IN(($before | split(","))[]) | not)][0] // ""')"
    [[ -n "${RELEASE_TAG}" ]] \
        || die "the bump left no draft release that was not already there. Check the bump run."
    note "draft release: ${RELEASE_TAG}"
    confirm "Publish ${RELEASE_TAG}? This is what triggers the publish workflow."
    state_put publish_baseline "$(latest_run_id feedstock-publish.yaml)"
    feedstock gh release edit "${RELEASE_TAG}" --draft=false
fi

if wants publish; then
    say "Watch the publish workflow"
    watch_new_run feedstock-publish.yaml "$(state_get publish_baseline)"
fi

if wants verify; then
    resolve_recipe
    say "Verify what the API holds"
    book="${WORK}/book.json"
    feedstock uv run bookshelf show "${VOLUME}@${DATASET_VERSION}" --json "${API_ARGS[@]}" \
        >"${book}" \
        || die "${VOLUME}@${DATASET_VERSION} does not resolve to a published book." \
            "An unauthenticated session cannot see a hidden one, so try 'bookshelf auth login' first."

    status="$(jq -r .status "${book}")"
    [[ "${status}" == "published" ]] || die "${VOLUME}@${DATASET_VERSION} is ${status}, not published"

    before="$(state_get before_editions)"
    after="$(editions_now)"
    is_number "${before}" || die "no edition count was taken before the release," \
        "so this proves only that a book is there, not that this run published one." \
        "Re-run from preflight."
    note "editions before: ${before}"
    note "editions now:    ${after}"
    if [[ "${after}" -le "${before}" ]]; then
        [[ "${ALLOW_UNCHANGED}" == "true" ]] \
            || die "the book did not move, so the publish wrote nothing." \
                "Publishing an unchanged book is idempotent," \
                "so a release that changes nothing the bundle covers lands no new edition." \
                "Pass --allow-unchanged when that is what you expect."
        note "no new edition, which --allow-unchanged accepts"
    fi

    jq -r '"    address:   \(.address)\n    status:    \(.status)\n    published: \(.published_at)\n    resources: \([.resources[].name] | join(", "))"' "${book}"

    state_drop before_editions

    say "Pilot passed"
    note "template ${TEMPLATE_REF} generated a feedstock that recorded, released and published."
fi
