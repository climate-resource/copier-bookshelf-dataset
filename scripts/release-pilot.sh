#!/usr/bin/env bash
# Pilot a template release end to end against a real feedstock.
#
# Takes a tagged release of this template, updates the pilot feedstock onto it,
# records the book locally, bumps and tags the feedstock, publishes the draft
# release, watches the publish workflow, and asks the API what landed.
#
# Every step is idempotent enough to re-run, and any step can be skipped with
# --from and --to when a run stops half way.
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

usage() {
    sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    cat <<'EOF'

Options:
  --template-ref TAG     Template tag to pilot. Defaults to the latest release of this repository.
  --feedstock PATH       Feedstock clone to pilot with. Defaults to ../bookshelf-test.
  --dataset-version VER  Book version to record locally. Defaults to the last entry in the recipe.
  --bump-rule RULE       Rule passed to the feedstock's Bump version workflow. Defaults to patch.
  --api-url URL          Bookshelf deployment to verify against. Defaults to the CLI's own default.
  --from STEP            First step to run. One of: preflight update record push bump release publish verify.
  --to STEP              Last step to run.
  --yes                  Do not prompt before pushing or publishing the release.
  --trust                Pass --trust to copier. Needed when the feedstock was generated from a
                         template version that declared tasks. Read them before trusting them.
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
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

say() { printf '\n=== %s ===\n' "$*"; }
note() { printf '    %s\n' "$*"; }
die() { printf '\nrelease-pilot: %s\n' "$*" >&2; exit 1; }

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
    local index; index="$(step_index "$1")"
    [[ "${index}" -ge "${FROM_INDEX}" && "${index}" -le "${TO_INDEX}" ]]
}

# The feedstock's own venv holds the bookshelf CLI, so every call runs from there.
feedstock() { (cd "${FEEDSTOCK}" && "$@"); }

API_ARGS=()
if [[ -n "${API_URL}" ]]; then
    API_ARGS=(--api-url "${API_URL}")
fi

recipe_field() {
    # Reads one dotted path out of the recipe, tolerating the pre-volume recipe format.
    feedstock uv run --with pyyaml python - "$1" <<'PY'
import sys, yaml

path = sys.argv[1].split(".")
with open("bookshelf.yaml") as handle:
    document = yaml.safe_load(handle)
node = document
for key in path:
    if not isinstance(node, dict) or key not in node:
        print("")
        sys.exit(0)
    node = node[key]
print(node if not isinstance(node, (dict, list)) else "")
PY
}

latest_book_version() {
    feedstock uv run --with pyyaml python - <<'PY'
import yaml

with open("bookshelf.yaml") as handle:
    document = yaml.safe_load(handle)
books = document.get("books") or []
print(books[-1]["version"] if books else "")
PY
}

latest_run_id() {
    # Newest run of one workflow, or 0 when the workflow has never run.
    feedstock gh run list --workflow "$1" --limit 1 --json databaseId \
        --jq '.[0].databaseId // 0'
}

watch_new_run() {
    # Waits for a run of $1 newer than $2 to appear, then follows it to its exit code.
    local workflow="$1" baseline="$2" waited=0 run_id
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

[[ -d "${FEEDSTOCK}/.git" ]] || die "no git repository at ${FEEDSTOCK}. Pass --feedstock PATH."

if wants preflight; then
    say "Preflight"
    for tool in gh jq uv git; do
        command -v "${tool}" >/dev/null || die "${tool} is not on PATH"
    done
    gh auth status >/dev/null 2>&1 || die "gh is not authenticated. Run: gh auth login"

    [[ -z "$(feedstock git status --porcelain)" ]] \
        || die "${FEEDSTOCK} has uncommitted changes. Commit or stash them first."
    branch="$(feedstock git rev-parse --abbrev-ref HEAD)"
    [[ "${branch}" == "main" ]] || die "${FEEDSTOCK} is on ${branch}, not main"
    feedstock git fetch --quiet --tags origin
    [[ "$(feedstock git rev-parse HEAD)" == "$(feedstock git rev-parse origin/main)" ]] \
        || die "${FEEDSTOCK} is not level with origin/main"

    if [[ -z "${TEMPLATE_REF}" ]]; then
        TEMPLATE_REF="$(gh release view --repo climate-resource/copier-bookshelf-dataset \
            --json tagName --jq .tagName)"
        note "no --template-ref given, using the latest release"
    fi
    gh api "repos/climate-resource/copier-bookshelf-dataset/git/ref/tags/${TEMPLATE_REF}" \
        >/dev/null 2>&1 || die "${TEMPLATE_REF} is not a tag on the template repository"
    # A first publish into a new volume fails with "not found", so check before releasing.
    if ! feedstock uv run bookshelf show "$(recipe_field volume.name)" \
        "${API_ARGS[@]}" >/dev/null 2>&1; then
        note "warning: the API has no volume for this feedstock yet."
        note "         A first publish needs it created once with 'bookshelf volume create'."
        note "         An unauthenticated session cannot see a hidden volume, so this may be a false alarm."
    fi

    note "template ref:  ${TEMPLATE_REF}"
    note "feedstock:     ${FEEDSTOCK}"
    note "publish target: $(feedstock gh repo view --json nameWithOwner --jq .nameWithOwner)"
fi

[[ -n "${TEMPLATE_REF}" ]] || TEMPLATE_REF="$(gh release view \
    --repo climate-resource/copier-bookshelf-dataset --json tagName --jq .tagName)"

if wants update; then
    say "Update the feedstock onto ${TEMPLATE_REF}"
    copier_args=(--vcs-ref "${TEMPLATE_REF}" --defaults --conflict inline)
    [[ "${TRUST}" == "true" ]] && copier_args+=(--trust)
    feedstock uvx copier update "${copier_args[@]}" || die "copier update failed (exit $?).
    Exit 4 means the template version this feedstock was generated from declares tasks.
    Copier replays that old version during an update, so it asks for consent.
    Read the tasks on that ref, then re-run with --trust."
    if feedstock git grep -qI -e '<<<<<<<' -e '>>>>>>>' -- . 2>/dev/null; then
        feedstock git grep -lI -e '<<<<<<<' -- .
        die "the update left conflict markers. Resolve them, then re-run with --from record."
    fi
    feedstock uv lock
    feedstock uv sync
    feedstock git --no-pager diff --stat
fi

VOLUME=""
BEFORE_EDITIONS=""
BEFORE_TAKEN_EARLY="false"

resolve_recipe() {
    # Reads the volume and the book version out of the updated recipe, once.
    [[ -n "${VOLUME}" ]] && return 0
    VOLUME="$(recipe_field volume.name)"
    [[ -n "${VOLUME}" ]] || VOLUME="$(recipe_field collection)"
    [[ -n "${VOLUME}" ]] || die "cannot read the volume name out of ${FEEDSTOCK}/bookshelf.yaml"
    [[ -n "${DATASET_VERSION}" ]] || DATASET_VERSION="$(latest_book_version)"
    [[ -n "${DATASET_VERSION}" ]] \
        || die "cannot read a book version out of the recipe. Pass --dataset-version."

    # What the API holds now, so the verify step can say what the release moved.
    feedstock uv run bookshelf show "${VOLUME}" --json "${API_ARGS[@]}" \
        >"${WORK}/before.json" 2>/dev/null || echo '{}' >"${WORK}/before.json"
    BEFORE_EDITIONS="$(jq '[.versions[]?.editions[]?] | length' "${WORK}/before.json")"
    note "the API holds ${BEFORE_EDITIONS} edition(s) of ${VOLUME} today"
}

if wants record; then
    resolve_recipe
    BEFORE_TAKEN_EARLY="true"
    say "Record ${VOLUME}@${DATASET_VERSION} locally"
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
    baseline="$(latest_run_id bump.yaml)"
    feedstock gh workflow run bump.yaml -f "bump_rule=${BUMP_RULE}"
    watch_new_run bump.yaml "${baseline}"
    feedstock git fetch --quiet --tags origin
fi

RELEASE_TAG="$(feedstock gh release list --limit 20 --json tagName,isDraft \
    --jq 'map(select(.isDraft)) | .[0].tagName // ""')"

if wants release; then
    say "Publish the draft release"
    [[ -n "${RELEASE_TAG}" ]] || die "no draft release to publish. Check the bump run."
    note "draft release: ${RELEASE_TAG}"
    confirm "Publish ${RELEASE_TAG}? This is what triggers the publish workflow."
    baseline="$(latest_run_id feedstock-publish.yaml)"
    feedstock gh release edit "${RELEASE_TAG}" --draft=false
    echo "${baseline}" >"${WORK}/publish-baseline"
fi

if wants publish; then
    say "Watch the publish workflow"
    baseline="$(cat "${WORK}/publish-baseline" 2>/dev/null || echo 0)"
    watch_new_run feedstock-publish.yaml "${baseline}"
fi

if wants verify; then
    resolve_recipe
    say "Verify what the API holds"
    AFTER="${WORK}/after.json"
    feedstock uv run bookshelf show "${VOLUME}" --json "${API_ARGS[@]}" >"${AFTER}" \
        || die "the API does not know about ${VOLUME}. Authenticate with: bookshelf auth login"

    after_editions="$(jq '[.versions[]?.editions[]?] | length' "${AFTER}")"
    # The before count only means anything when it was taken before the release.
    if [[ "${BEFORE_TAKEN_EARLY}" == "true" ]]; then
        note "editions before: ${BEFORE_EDITIONS}"
    fi
    note "editions now:    ${after_editions}"

    book="${WORK}/book.json"
    feedstock uv run bookshelf show "${VOLUME}@${DATASET_VERSION}" --json "${API_ARGS[@]}" >"${book}" \
        || die "${VOLUME}@${DATASET_VERSION} does not resolve to a published book"

    status="$(jq -r .status "${book}")"
    [[ "${status}" == "published" ]] || die "${VOLUME}@${DATASET_VERSION} is ${status}, not published"

    jq -r '"    address:   \(.address)\n    status:    \(.status)\n    published: \(.published_at)\n    resources: \([.resources[].name] | join(", "))"' "${book}"

    say "Pilot passed"
    note "template ${TEMPLATE_REF} generated a feedstock that recorded, released and published."
fi
