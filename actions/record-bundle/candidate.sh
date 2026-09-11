#!/usr/bin/env bash
# Builds the candidate a run validates and reports its identity as step outputs.
# A pull request is its head merged with main, pinned by MAIN_SHA once the first job has resolved it.
set -euo pipefail

if [[ "${EVENT}" == "pull_request" ]]; then
  main_sha="${MAIN_SHA:-}"
  git fetch --quiet origin "${MAIN_REF}"
  if [[ -z "${main_sha}" ]]; then
    main_sha="$(git rev-parse "origin/${MAIN_REF}")"
  fi
  head_sha="${PR_HEAD_SHA}"
  git checkout -q "${head_sha}"
  if ! git -c user.name=ci -c user.email=ci@invalid merge -q --no-ff --no-edit "${main_sha}"; then
    echo "conflict=true" >> "${GITHUB_OUTPUT}"
    echo "::error::${head_sha} does not merge cleanly with ${MAIN_REF} at ${main_sha}"
    exit 1
  fi
else
  head_sha="${GITHUB_SHA}"
  main_sha="${GITHUB_SHA}"
fi

candidate_tree="$(git rev-parse 'HEAD^{tree}')"
if [[ -n "${EXPECTED_TREE:-}" && "${candidate_tree}" != "${EXPECTED_TREE}" ]]; then
  echo "::error::rebuilt candidate tree ${candidate_tree} differs from ${EXPECTED_TREE}"
  exit 1
fi

{
  echo "conflict=false"
  echo "head-sha=${head_sha}"
  echo "main-sha=${main_sha}"
  echo "candidate-tree=${candidate_tree}"
} >> "${GITHUB_OUTPUT}"
