"""Security and trust guards on this repository's workflows.

The workflows themselves are exercised by CI and actionlint,
so these check only the properties a reviewer could miss in a diff.
"""

from typing import Any

import yaml
from conftest import ROOT

WORKFLOWS = ROOT / ".github" / "workflows"
FEEDSTOCK_CI = WORKFLOWS / "feedstock-ci.yaml"


def feedstock_ci() -> dict[Any, Any]:
    """Return the parsed reusable feedstock workflow."""
    return yaml.safe_load(FEEDSTOCK_CI.read_text())


def steps_using(job: dict[str, Any], action: str) -> list[dict[str, Any]]:
    """Return the steps of a job that call an action, whatever its ref."""
    return [step for step in job.get("steps", []) if action in step.get("uses", "")]


def test_the_reusable_workflow_is_call_only_and_takes_no_secrets() -> None:
    """Feedstock CI runs only when called and authenticates through OIDC alone."""
    workflow = feedstock_ci()

    assert set(workflow[True]) == {"workflow_call"}
    assert "secrets" not in (workflow[True]["workflow_call"] or {})
    assert "secrets." not in FEEDSTOCK_CI.read_text()


def test_only_the_record_and_preview_jobs_can_mint_an_oidc_token() -> None:
    """The other jobs run pull request code without needing to reach the platform."""
    workflow = feedstock_ci()

    assert "id-token" not in workflow["permissions"]
    minting = {
        name
        for name, job in workflow["jobs"].items()
        if job.get("permissions", {}).get("id-token") == "write"
    }
    assert minting == {"record", "preview"}


def test_the_preview_job_runs_no_pull_request_code() -> None:
    """The upload job checks out only this template."""
    preview = feedstock_ci()["jobs"]["preview"]
    checkouts = steps_using(preview, "actions/checkout")

    assert "head.repo.full_name == github.repository" in preview["if"]
    assert [step["with"].get("repository") for step in checkouts] == [
        "${{ job.workflow_repository }}",
    ]


def test_every_job_loads_the_helpers_from_its_own_revision() -> None:
    """A helper from another revision could disagree with the workflow calling it."""
    for name, job in feedstock_ci()["jobs"].items():
        for step in steps_using(job, "actions/checkout"):
            if step["with"].get("path") == ".copier-bookshelf-dataset":
                assert step["with"]["repository"] == "${{ job.workflow_repository }}"
                assert step["with"]["ref"] == "${{ job.workflow_sha }}", name


def test_every_artifact_upload_overwrites() -> None:
    """A re-run of a failed leg uploads under the name its first attempt used."""
    for name, job in feedstock_ci()["jobs"].items():
        for step in steps_using(job, "actions/upload-artifact"):
            assert step["with"].get("overwrite") is True, name


def test_no_workflow_carries_a_publish_credential() -> None:
    """The platform publishes a merged pull request, so CI carries no publish path."""
    assert not (WORKFLOWS / "feedstock-publish.yaml").exists()

    for workflow in WORKFLOWS.glob("*.yaml"):
        definition = workflow.read_text()

        assert "BOOKSHELF_CLIENT_ID" not in definition
        assert "BOOKSHELF_CLIENT_SECRET" not in definition
        assert "grant_type=client_credentials" not in definition
