"""
Test directories made with copier-template-tester (ctt)

In theory, these tests should only be run after we have run ctt to ensure the
latest changes are picked up. In practice, even if you forget to run ctt the
pre-commit hooks and CI will make sure you don't miss things completely.
"""

import os
import subprocess
from pathlib import Path

import pytest

CTT_DIR = Path(__file__).parent / "regression" / "ctt"

ctt_directories = pytest.mark.parametrize(
    "ctt_dir", [pytest.param(CTT_DIR.absolute() / d, id=d) for d in os.listdir(CTT_DIR)]
)


def setup_venv(ctt_dir, env):
    try:
        del env["VIRTUAL_ENV"]
    except KeyError:
        pass

    subprocess.run(("make", "virtual-environment"), cwd=ctt_dir, env=env, check=True)

    lock_file = ctt_dir / "uv.lock"
    assert lock_file.exists()


@ctt_directories
def test_towncrier_draft(ctt_dir, tmp_path):
    env = os.environ
    setup_venv(ctt_dir, env)

    res = subprocess.run(
        (
            "uvx",
            "towncrier",
            "build",
            "--draft",
            "--version",
            "0.2.0",
        ),
        cwd=ctt_dir,
        env=env,
        stdout=subprocess.PIPE,
        check=True,
    )

    assert "Example Dataset 0.2.0" in res.stdout.decode()


@ctt_directories
def test_run(ctt_dir):
    env = os.environ
    setup_venv(ctt_dir, env)

    subprocess.run(
        (
            "make",
            "run",
        ),
        cwd=ctt_dir,
        env=env,
        check=True,
    )
    out_dir = ctt_dir / "out"

    assert out_dir.exists()
