"""Tests that answers survive the trip into the generated metadata files.

Answers are free text. They land in TOML, YAML and Markdown, so every one of those
files has to parse and give the answer back unchanged.
"""

import ast
import tomllib

import pytest
import yaml
from conftest import Feedstock

TOML_FILES = ("pyproject.toml", "towncrier.toml", "ruff.toml")


@pytest.mark.parametrize("name", TOML_FILES)
def test_generated_toml_parses(feedstock: Feedstock, name: str) -> None:
    """A quote or a colon in an answer must not break the file it lands in."""
    assert tomllib.loads(feedstock.read(name))


def test_generated_recipe_parses_and_round_trips_the_authors(
    feedstock: Feedstock,
) -> None:
    """The recipe carries the author exactly as answered."""
    recipe = yaml.safe_load(feedstock.read("bookshelf.yaml"))

    assert recipe["collection"] == feedstock.answers["dataset_name"]
    assert recipe["license"] == "MIT"
    assert recipe["visibility"] == "public"
    assert recipe["notebook"] == "build.py"
    assert recipe["authors"] == [
        {
            "name": feedstock.answers["author"],
            "email": feedstock.answers["author_email"],
        }
    ]


def test_generated_workflows_parse(feedstock: Feedstock) -> None:
    """The generated callers are valid YAML with the triggers they claim."""
    for name in ("feedstock-ci.yaml", "feedstock-publish.yaml", "bump.yaml"):
        workflow = yaml.safe_load(feedstock.read(f".github/workflows/{name}"))
        assert workflow["jobs"]


def test_generated_pyproject_round_trips_the_name_and_description(
    feedstock: Feedstock,
) -> None:
    """The package name and description come straight from the answers."""
    project = tomllib.loads(feedstock.read("pyproject.toml"))["project"]

    assert project["name"] == f"bookshelf-{feedstock.answers['dataset_name']}"
    assert project["description"] == feedstock.answers["dataset_description"]


def test_generated_towncrier_round_trips_the_human_name(feedstock: Feedstock) -> None:
    """Changelog titles carry the human name, which may contain quotes."""
    towncrier = tomllib.loads(feedstock.read("towncrier.toml"))["tool"]["towncrier"]

    assert towncrier["name"] == f"bookshelf-{feedstock.answers['dataset_name']}"
    assert towncrier["title_format"] == (
        f"## {feedstock.answers['dataset_name_human']} {{version}} ({{project_date}})"
    )
    assert feedstock.answers["project_url"] in towncrier["issue_format"]


def test_generated_readme_leads_with_the_human_name_and_description(
    feedstock: Feedstock,
) -> None:
    """The README header is the human name, not the machine one."""
    readme = feedstock.read("README.md")

    assert readme.startswith(f"# {feedstock.answers['dataset_name_human']}\n")
    assert feedstock.answers["dataset_description"] in readme


def test_generated_build_file_is_valid_python(feedstock: Feedstock) -> None:
    """The build file is executed by the recorder, so it has to parse."""
    assert ast.parse(feedstock.read("build.py")).body


def test_no_generated_file_carries_unrendered_template_syntax(
    feedstock: Feedstock,
) -> None:
    """A stray delimiter means an answer never reached the generated project."""
    delimiters = ("{{", "}}", "{%", "{#")
    offenders = [
        name
        for name in feedstock.shipped()
        # The workflow templates deliberately ship GitHub Actions expressions,
        # which share Jinja's delimiters.
        if not name.startswith(".github/")
        and any(delimiter in feedstock.read(name) for delimiter in delimiters)
    ]

    assert not offenders


def test_answers_file_records_every_question(feedstock: Feedstock) -> None:
    """Copier updates replay the answers, so all of them have to be written down."""
    questions = {
        "author",
        "author_email",
        "dataset_name",
        "dataset_name_human",
        "dataset_description",
        "project_url",
    }

    assert questions <= set(feedstock.answers)
