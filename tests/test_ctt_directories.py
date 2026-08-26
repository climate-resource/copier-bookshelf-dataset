"""
Test directories made with copier-template-tester (ctt)

In theory, these tests should only be run after we have run ctt to ensure the
latest changes are picked up. In practice, even if you forget to run ctt the
pre-commit hooks and CI will make sure you don't miss things completely.

A rendered fixture is files and nothing else, so each one is copied into a temporary
directory and prepared with `make initial-setup` before it can record anything.
Preparing and recording are the expensive parts, so both happen once per session.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import BUNDLE, FEEDSTOCKS, VERSION, Feedstock

pytestmark = pytest.mark.slow

# The recorder adds these itself, so they are not what the build file registered.
DOCUMENTS = frozenset({"build.ipynb", "build.html"})

# uv resolves against an active environment, so this repository's own venv is dropped
# rather than inherited by a generated feedstock.
ENV = {name: value for name, value in os.environ.items() if name != "VIRTUAL_ENV"}


@pytest.fixture(scope="session")
def workspaces(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Prepare each rendered fixture the way a new feedstock's owner would."""
    prepared = {}

    for generated in FEEDSTOCKS:
        workspace = tmp_path_factory.mktemp(generated.name) / generated.name
        shutil.copytree(generated.path, workspace)

        subprocess.run(("make", "initial-setup"), cwd=workspace, env=ENV, check=True)
        assert (workspace / "uv.lock").exists()
        assert (workspace / ".git").exists()

        # `uv sync` rather than `make virtual-environment`, because installing the
        # pre-commit hooks proves nothing here and fails on a machine that sets
        # core.hooksPath globally.
        subprocess.run(("uv", "sync", "--locked"), cwd=workspace, env=ENV, check=True)
        prepared[generated.name] = workspace

    return prepared


def test_initial_setup_is_safe_to_re_run(workspaces: dict[str, Path]) -> None:
    """A second run must not relock, re-add the remote or make another commit."""
    workspace = workspaces[min(workspaces)]

    before = subprocess.run(
        ("git", "rev-list", "--count", "HEAD"),
        cwd=workspace,
        env=ENV,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout
    lock = (workspace / "uv.lock").read_bytes()

    subprocess.run(("make", "initial-setup"), cwd=workspace, env=ENV, check=True)

    after = subprocess.run(
        ("git", "rev-list", "--count", "HEAD"),
        cwd=workspace,
        env=ENV,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout

    assert after == before
    assert (workspace / "uv.lock").read_bytes() == lock


@pytest.fixture(scope="session")
def recorded(workspaces: dict[str, Path]) -> dict[str, dict[str, Any]]:
    """Record every prepared feedstock and return the bundle manifests."""
    manifests = {}

    for name, workspace in workspaces.items():
        shutil.rmtree(workspace / "bundle", ignore_errors=True)

        subprocess.run(("make", "run"), cwd=workspace, env=ENV, check=True)

        manifest = workspace / BUNDLE / "manifest.lock"
        assert manifest.exists()
        manifests[name] = yaml.safe_load(manifest.read_text())

    return manifests


def registered(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the resources the build file registered, keyed by name.

    The recorder adds the executed notebook and its rendering, which the build file
    does not register and does not name.
    """
    return {
        resource["name"]: resource
        for resource in manifest["resources"]
        if resource["name"] not in DOCUMENTS
    }


def test_towncrier_draft(feedstock: Feedstock, workspaces: dict[str, Path]):
    res = subprocess.run(
        (
            "uvx",
            "towncrier",
            "build",
            "--draft",
            "--version",
            "0.2.0",
        ),
        cwd=workspaces[feedstock.name],
        env=ENV,
        stdout=subprocess.PIPE,
        check=True,
    )

    expected = f"{feedstock.answers['dataset_name_human']} 0.2.0"
    assert expected in res.stdout.decode()


def test_run(
    feedstock: Feedstock,
    recorded: dict[str, dict[str, Any]],
    workspaces: dict[str, Path],
):
    """Recording produces a bundle whose book is the one the recipe describes."""
    book = recorded[feedstock.name]["book"]

    assert (workspaces[feedstock.name] / BUNDLE).exists()
    assert book["volume"] == feedstock.answers["dataset_name"]
    assert book["version"] == VERSION
    assert book["visibility"] == "public"
    assert book["license"] == "CC-BY-4.0"
    assert book["authors"] == [
        {
            "name": feedstock.answers["author"],
            "email": feedstock.answers["author_email"],
        }
    ]


def test_recorded_book_carries_the_resolved_discovery_metadata(
    feedstock: Feedstock, recorded: dict[str, dict[str, Any]]
):
    """`defaults:` is merged onto the book before it is recorded."""
    book = recorded[feedstock.name]["book"]

    assert book["discovery"]["title"] == feedstock.answers["dataset_name_human"]
    assert book["discovery"]["repository_url"] == feedstock.answers["project_url"]
    assert book["discovery"]["publisher"] == "Climate Resource"


def test_recorded_bundle_attaches_the_processed_resource(
    feedstock: Feedstock, recorded: dict[str, dict[str, Any]]
):
    """The book entry named `data` is the resource the build file wrote."""
    manifest = recorded[feedstock.name]

    assert "data" in registered(manifest)
    assert "data" in {entry["name"] for entry in manifest["book"]["entries"]}


def test_recorded_bundle_carries_the_declared_provenance(
    feedstock: Feedstock, recorded: dict[str, dict[str, Any]]
):
    """Both resources are recorded, and the processed one records what it used."""
    resources = registered(recorded[feedstock.name])

    assert set(resources) == {"raw", "data"}

    raw = resources["raw"]
    data = resources["data"]

    # A checked-in input is catalogued as a pointer at its path, never re-hosted.
    assert raw["kind"] == "pointer"
    assert raw["external_uri"] == "inputs/raw.csv"
    assert raw["generated"] is False
    assert raw["type"] == "tabular"
    assert data["generated"] is True
    assert data["type"] == "timeseries"
    assert data["used"] == ["raw"]

    # Processing doubles the values, so the two resources cannot hash the same.
    assert raw["hash"].startswith("sha256:")
    assert data["hash"].startswith("sha256:")
    assert raw["hash"] != data["hash"]


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

    assert len(set(hashes)) == len(hashes)
