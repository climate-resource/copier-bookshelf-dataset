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

import pytest
import yaml
from conftest import FEEDSTOCKS, Feedstock

# The version the generated recipe declares, and the bundle directory it lands in.
VERSION = "v0.1.0"
BUNDLE = f"bundle/{VERSION}"

# The recorder adds these itself, so they are not what the build file registered.
DOCUMENTS = frozenset({"build.ipynb", "build.html"})


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

        manifest = feedstock.path / BUNDLE / "manifest.lock"
        assert manifest.exists()
        manifests[feedstock.name] = yaml.safe_load(manifest.read_text())

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

    assert (feedstock.path / BUNDLE).exists()
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
