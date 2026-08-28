"""Public contract tests for the colocated actions and this repository's workflows."""

import json
import re

from conftest import ACTION, ROOT, uses_lines

WORKFLOWS = ROOT / ".github" / "workflows"


def test_record_bundle_composite_owns_the_offline_build_path() -> None:
    """The composite installs, records, caches inputs, and validates the bundle."""
    action = (ACTION / "action.yml").read_text()

    assert 'using: "composite"' in action
    assert "astral-sh/setup-uv@v8.3.2" in action
    assert "actions/cache@v6" in action
    assert "uv sync --locked" in action
    assert "uv run bookshelf record" in action
    assert "uv run bookshelf validate" in action
    assert 'python3 "${GITHUB_ACTION_PATH}/cache_key.py"' in action
    assert 'uv run python "${GITHUB_ACTION_PATH}/recipe_versions.py"' in action


def test_the_composite_action_ships_only_its_recipe_helpers() -> None:
    """The CLI owns record and validate, so no bundle script sits beside it.

    The two helpers stay because both read the recipe for a CI concern:
    what to key the input cache on, and which versions to record.
    """
    assert sorted(path.name for path in ACTION.glob("*.py")) == [
        "cache_key.py",
        "recipe_versions.py",
    ]


def test_the_composite_action_records_every_version_by_default() -> None:
    """The recipe is the one place versions are written down."""
    action = (ACTION / "action.yml").read_text()

    assert "for version in ${VERSIONS}; do" in action
    assert 'bundle="${BUNDLE}/${version}"' in action
    assert '--version "${version}"' in action


def test_the_composite_action_reports_the_bundle_directories_it_wrote() -> None:
    """A caller replays the paths it was given rather than joining them itself."""
    action = (ACTION / "action.yml").read_text()

    assert "bundles:" in action
    assert 'echo "bundles=${bundles}" >> "${GITHUB_OUTPUT}"' in action


def test_the_composite_action_takes_the_build_file_from_the_recipe() -> None:
    """`build: notebook:` is the one place the build file is written down.

    A second default here could disagree with what `make run` executes locally.
    """
    action = (ACTION / "action.yml").read_text()

    assert "build-file" not in action
    assert "uv run bookshelf record \\\n" in action


def test_the_composite_action_caches_where_the_sdk_fetches_into() -> None:
    """The SDK caches under a platform directory that no runner keeps between jobs."""
    action = (ACTION / "action.yml").read_text()

    assert "BOOKSHELF_CACHE_DIR: .cache" in action
    assert "path: .cache" in action


def test_ci_reusable_workflow_is_credential_free_and_call_only() -> None:
    """Feedstock CI runs only when called and exposes no credential surface."""
    workflow = (WORKFLOWS / "feedstock-ci.yaml").read_text()

    assert "workflow_call:" in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
    assert "workflow_dispatch:" not in workflow
    assert "actions/checkout@v6" in workflow
    assert "./.copier-bookshelf-dataset/actions/record-bundle" in workflow
    assert "secrets:" not in workflow
    assert "BOOKSHELF_TOKEN" not in workflow


def test_publish_reusable_workflow_uses_deploy_environment_secrets() -> None:
    """Publish exchanges deploy environment M2M credentials and replays."""
    workflow = (WORKFLOWS / "feedstock-publish.yaml").read_text()

    assert "workflow_call:" in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
    assert "workflow_dispatch:" not in workflow
    assert "api-base-url:" in workflow
    assert "https://api.climateresource.com.au/bookshelf" in workflow
    assert "BOOKSHELF_CLIENT_ID:" in workflow
    assert "BOOKSHELF_CLIENT_SECRET:" in workflow
    assert "environment: deploy" in workflow
    assert "grant_type=client_credentials" in workflow
    assert "./.copier-bookshelf-dataset/actions/record-bundle" in workflow
    assert 'uv run bookshelf publish "${bundle}"' in workflow
    assert "for bundle in ${BUNDLES}; do" in workflow
    assert "Publish outcome" in workflow

    # The credential reaches the CLI through the environment.
    # A token on argv is visible in the process list and in the job log.
    assert "--token" not in workflow
    assert "BOOKSHELF_TOKEN: ${{ steps.token.outputs.token }}" in workflow


def test_reusable_workflows_checkout_their_own_matching_revision() -> None:
    """A called workflow loads the composite action from the same pinned ref."""
    for name in ("feedstock-ci.yaml", "feedstock-publish.yaml"):
        workflow = (WORKFLOWS / name).read_text()

        assert "repository: ${{ job.workflow_repository }}" in workflow
        assert "ref: ${{ job.workflow_sha }}" in workflow
        assert "path: .copier-bookshelf-dataset" in workflow


def test_actionlint_is_part_of_the_existing_ci_and_immutably_pinned() -> None:
    """The repository CI lints all workflows with an auditable action ref."""
    workflow = (WORKFLOWS / "ci.yaml").read_text()

    assert "actionlint:" in workflow
    assert (
        "raven-actions/actionlint@3d39aea434753780c3b3d4a1a31c854b4dbf49d7" in workflow
    )


def test_feedstock_automation_defaults_to_python_312() -> None:
    """Every entry point selects Python 3.12 when callers do not override it."""
    entry_points = (
        WORKFLOWS / "feedstock-ci.yaml",
        WORKFLOWS / "feedstock-publish.yaml",
        ACTION / "action.yml",
    )

    for entry_point in entry_points:
        definition = entry_point.read_text()
        assert 'default: "3.12"' in definition
        assert 'default: "3.11"' not in definition


def test_environment_secret_model_is_documented_without_a_handoff_file() -> None:
    """The README owns deploy environment guidance without a handoff document."""
    readme = (ROOT / "README.md").read_text()

    assert "secrets: inherit" in readme
    assert "deploy" in readme
    assert "environment secrets" in readme
    assert not (ROOT / "HANDOFF.md").exists()


def test_action_scripts_use_native_python_311_annotations() -> None:
    """Action scripts do not carry an unnecessary future annotations import."""
    for script in ACTION.glob("*.py"):
        assert "from __future__ import annotations" not in script.read_text()


SHARED_BUMP = re.compile(
    r"uses: climate-resource/github-actions"
    r"/\.github/workflows/bump\.yaml@v\d+\.\d+\.\d+"
)


def test_bump_delegates_to_the_shared_actions_repository() -> None:
    """Both bump workflows call the shared workflow, rather than inlining its steps.

    The tag is not spelled out here, because Renovate moves it.
    """
    callers = (
        WORKFLOWS / "bump.yaml",
        ROOT / "template" / ".github" / "workflows" / "bump.yaml",
    )

    for caller in callers:
        shared = [
            line
            for line in uses_lines(caller)
            if "climate-resource/github-actions" in line
        ]

        assert len(shared) == 1, (caller.relative_to(ROOT), shared)
        assert SHARED_BUMP.fullmatch(shared[0]), (caller.relative_to(ROOT), shared[0])


def test_this_repository_has_a_renovate_config() -> None:
    """Renovate keeps the pins inside `template/` moving, so it needs a config."""
    config = json.loads((ROOT / "renovate.json").read_text())

    managed = {manager["description"] for manager in config["customManagers"]}
    assert managed, "no custom managers, so the template's pins would never move"
