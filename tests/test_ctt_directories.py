"""
Test directories made with copier-template-tester (ctt)

In theory, these tests should only be run after we have run ctt to ensure the
latest changes are picked up. In practice, even if you forget to run ctt the
pre-commit hooks and CI will make sure you don't miss things completely.

Recording is the expensive part, so every generated feedstock is recorded once for
the whole session and the tests read the manifest that came out.
"""

import os
import shutil
import subprocess
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import pytest
import yaml
from conftest import FEEDSTOCKS, Feedstock

# The version the generated build file declares.
VERSION = "v0.1.0"


def setup_venv(feedstock: Feedstock, env):
    if not (feedstock.path / "uv.lock").exists():
        pytest.skip("the generated feedstock has no lock file to sync against")

    try:
        del env["VIRTUAL_ENV"]
    except KeyError:
        pass

    subprocess.run(
        ("make", "virtual-environment"), cwd=feedstock.path, env=env, check=True
    )

    lock_file = feedstock.path / "uv.lock"
    assert lock_file.exists()


@pytest.fixture(scope="session")
def recorded() -> dict[str, dict[str, Any]]:
    """Record every generated feedstock and return the bundle manifests."""
    env = os.environ
    manifests = {}

    for feedstock in FEEDSTOCKS:
        setup_venv(feedstock, env)

        bundle_dir = feedstock.path / "bundle"
        shutil.rmtree(bundle_dir, ignore_errors=True)

        subprocess.run(("make", "run"), cwd=feedstock.path, env=env, check=True)

        assert bundle_dir.exists()
        manifests[feedstock.name] = yaml.safe_load(
            (bundle_dir / "manifest.lock").read_text()
        )

    return manifests


def registered(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the resources the build file registered, keyed by logical key.

    The recorder adds the executed notebook and its rendering, which the build file
    does not register and does not name.
    """
    return {
        resource["logical_key"]: resource
        for resource in manifest["resources"]
        if not resource["logical_key"].startswith("document/")
    }


def test_towncrier_draft(feedstock: Feedstock):
    env = os.environ
    setup_venv(feedstock, env)

    res = subprocess.run(
        (
            "uvx",
            "towncrier",
            "build",
            "--draft",
            "--version",
            "0.2.0",
        ),
        cwd=feedstock.path,
        env=env,
        stdout=subprocess.PIPE,
        check=True,
    )

    expected = f"{feedstock.answers['dataset_name_human']} 0.2.0"
    assert expected in res.stdout.decode()


def test_run(feedstock: Feedstock, recorded: dict[str, dict[str, Any]]):
    """Recording produces a bundle whose book is the one the recipe describes."""
    book = recorded[feedstock.name]["book"]

    assert (feedstock.path / "bundle").exists()
    assert book["volume"] == feedstock.answers["dataset_name"]
    assert book["version"] == VERSION
    assert book["visibility"] == "public"
    assert book["license"] == "MIT"
    assert book["authors"] == [
        {
            "name": feedstock.answers["author"],
            "email": feedstock.answers["author_email"],
        }
    ]


def test_recorded_bundle_attaches_the_processed_resource(
    feedstock: Feedstock, recorded: dict[str, dict[str, Any]]
):
    """The book entry named `data` points at the resource the build file attached."""
    manifest = recorded[feedstock.name]
    resources = registered(manifest)
    data = resources[f"{feedstock.answers['dataset_name']}/data-{VERSION}"]

    entries = {entry["name_in_book"]: entry for entry in manifest["book"]["entries"]}
    assert "data" in entries
    assert entries["data"]["tracking_id"] == data["tracking_id"]


def test_recorded_bundle_carries_the_declared_provenance(
    feedstock: Feedstock, recorded: dict[str, dict[str, Any]]
):
    """Both resources are recorded, and the processed one records what it used."""
    dataset_name = feedstock.answers["dataset_name"]
    resources = registered(recorded[feedstock.name])

    assert set(resources) == {
        f"{dataset_name}/raw-{VERSION}",
        f"{dataset_name}/data-{VERSION}",
    }

    raw = resources[f"{dataset_name}/raw-{VERSION}"]
    data = resources[f"{dataset_name}/data-{VERSION}"]

    assert raw["type"] == "tabular"
    assert data["type"] == "timeseries"
    assert {used["tracking_id"] for used in data["used"]} == {raw["tracking_id"]}

    # Processing doubles the values, so the two resources cannot hash the same.
    assert raw["hash"].startswith("sha256:")
    assert data["hash"].startswith("sha256:")
    assert raw["hash"] != data["hash"]


def test_recorded_identifiers_are_derived_from_the_project_url(
    feedstock: Feedstock, recorded: dict[str, dict[str, Any]]
):
    """The build file names its resources, so re-recording keeps the same ids."""
    dataset_name = feedstock.answers["dataset_name"]
    namespace = feedstock.answers["project_url"]
    manifest = recorded[feedstock.name]
    resources = registered(manifest)

    def derived(kind: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"{namespace}/{kind}/{VERSION}"))

    assert resources[f"{dataset_name}/raw-{VERSION}"]["tracking_id"] == derived("raw")
    assert resources[f"{dataset_name}/data-{VERSION}"]["tracking_id"] == derived("data")
    assert manifest["activity"]["activity_id"] == derived("build")


def test_recorded_resources_never_collide_between_feedstocks(
    recorded: dict[str, dict[str, Any]],
):
    """Two feedstocks must not record byte identical resources.

    This is the end of the chain the example input starts. The registered bytes are
    derived from it, so if the example were shared the recorded resources would
    deduplicate onto each other in a deployment.
    """
    hashes = [
        resource["hash"]
        for manifest in recorded.values()
        for resource in registered(manifest).values()
    ]
    tracking_ids = [
        resource["tracking_id"]
        for manifest in recorded.values()
        for resource in registered(manifest).values()
    ]

    assert len(set(hashes)) == len(hashes)
    assert len(set(tracking_ids)) == len(tracking_ids)
