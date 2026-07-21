"""Public contract tests for the colocated Bookshelf feedstock actions."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
ACTION = ROOT / "actions" / "record-bundle"
WORKFLOWS = ROOT / ".github" / "workflows"


def test_record_bundle_composite_owns_the_offline_build_path() -> None:
    """The composite installs, records, caches inputs, and validates the bundle."""
    action = (ACTION / "action.yml").read_text()

    assert 'using: "composite"' in action
    assert "climate-resource/github-actions/setup-uv@v1" in action
    assert "actions/cache@v4" in action
    assert "uv sync --locked" in action
    assert "bookshelf record" in action
    assert "validate_bundle.py" in action
    assert 'python3 "${GITHUB_ACTION_PATH}/cache_key.py"' in action
    assert "BOOKSHELF_ACTION_PATH" in action
    assert "contract" in action


def test_ci_reusable_workflow_is_credential_free_and_call_only() -> None:
    """Feedstock CI runs only when called and exposes no credential surface."""
    workflow = (WORKFLOWS / "feedstock-ci.yaml").read_text()

    assert "workflow_call:" in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
    assert "workflow_dispatch:" not in workflow
    assert "actions/checkout@v4" in workflow
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
    assert "publish_bundle.py" in workflow
    assert "Publish outcome" in workflow

    publisher = (ACTION / "publish_bundle.py").read_text()
    assert '"outcome": "no-op"' in publisher
    assert publisher.index('"outcome": "no-op"') < publisher.index(
        "artifacts = await replay"
    )


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
