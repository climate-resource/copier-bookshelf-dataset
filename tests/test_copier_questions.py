"""Tests for the questions, validators and tasks declared in copier.yaml.

The validators are Jinja templates that render an error message when an answer is
rejected, and render nothing when it is accepted. These tests render them the same way
Copier does, so a loosened pattern shows up here rather than in a generated feedstock.
"""

import re
import warnings

import jinja2
import pytest
from conftest import CASES, COPIER, QUESTIONS, ROOT
from jinja2_ansible_filters import AnsibleCoreFiltersExtension


def validator_environment() -> jinja2.Environment:
    """Build the environment Copier renders a validator in.

    Autoescaping stays off, because the rendered text is a terminal message rather
    than markup, and switching it on would stop reproducing what Copier does.
    """
    return jinja2.Environment(  # noqa: S701
        extensions=[AnsibleCoreFiltersExtension]
    )


def rejection(question: str, answer: object) -> str:
    """Render a question's validator, returning the error it reports."""
    template = validator_environment().from_string(COPIER[question]["validator"])
    return template.render(**{"dataset_name": "example", question: answer}).strip()


def test_validators_use_escape_sequences_jinja_understands() -> None:
    """Jinja decodes its string literals, so a bare \\S warns on every prompt."""
    environment = validator_environment()

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for question in QUESTIONS.values():
            if "validator" in question:
                environment.from_string(question["validator"])


def test_every_question_has_a_type_and_help() -> None:
    """A prompt without help is a prompt nobody can answer correctly."""
    assert set(QUESTIONS) == {
        "author",
        "author_email",
        "dataset_name",
        "dataset_name_human",
        "dataset_description",
        "project_url",
        "bookshelf_sdk_version",
        "extra_recipes",
    }

    for name, question in QUESTIONS.items():
        assert question["type"] == ("yaml" if name == "extra_recipes" else "str"), name
        assert question["help"].strip(), name
        assert "placeholder" in question or "default" in question, name


@pytest.mark.parametrize(
    "name",
    ["example", "primap-hist", "ngfs-scenarios-2024", "a1", "ar6-db"],
)
def test_dataset_name_accepts_lower_case_hyphenated_names(name: str) -> None:
    """Hyphens, digits and lower case letters are the supported alphabet."""
    assert not rejection("dataset_name", name)


@pytest.mark.parametrize(
    ("name", "why"),
    [
        ("Example", "capitals"),
        ("two words", "spaces"),
        ("under_scored", "underscores"),
        ("trailing.dot", "punctuation"),
        ("1leading-digit", "a leading digit"),
        ("x", "a single character"),
        ("", "an empty answer"),
        ("with/slash", "a path separator"),
        ("café", "non ascii letters"),
    ],
)
def test_dataset_name_rejects_everything_else(name: str, why: str) -> None:
    """The name becomes a package name and a logical key, so it stays restricted."""
    assert rejection("dataset_name", name), why


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/climate-resource/bookshelf-example",
        "https://www.github.com/climate-resource/bookshelf-example",
    ],
)
def test_project_url_accepts_github_https_urls(url: str) -> None:
    """Only GitHub is supported, because the workflows are GitHub Actions."""
    assert not rejection("project_url", url)


@pytest.mark.parametrize(
    ("url", "why"),
    [
        ("http://github.com/climate-resource/example", "plain http"),
        ("https://gitlab.com/climate-resource/example", "another forge"),
        ("git@github.com:climate-resource/example.git", "an ssh remote"),
        ("github.com/climate-resource/example", "no scheme"),
        ("", "an empty answer"),
    ],
)
def test_project_url_rejects_everything_else(url: str, why: str) -> None:
    """The URL becomes a git remote and a resource namespace, so it has to resolve."""
    assert rejection("project_url", url), why


def test_project_url_defaults_to_the_conventional_feedstock_repository() -> None:
    """A feedstock is named after its dataset, so the default writes itself."""
    default = COPIER["project_url"]["default"]

    assert "climate-resource/bookshelf-{{ dataset_name }}" in default


def test_every_ctt_answer_set_satisfies_the_validators() -> None:
    """The regression fixtures have to be answers a real user could give."""
    for case, answers in CASES.items():
        for question in ("dataset_name", "project_url"):
            assert not rejection(question, answers[question]), f"{case}/{question}"


def test_the_answer_sets_differ_in_the_answers_that_matter() -> None:
    """Generating the same feedstock twice would stress nothing."""
    for question in ("dataset_name", "project_url", "author"):
        values = [answers[question] for answers in CASES.values()]
        assert len(set(values)) == len(values), question


def test_the_template_declares_no_copier_tasks() -> None:
    """Tasks force `--trust`, which stops Renovate applying a template update."""
    assert COPIER["_subdirectory"] == "template"
    assert "_tasks" not in COPIER


def test_initial_setup_prepares_what_recording_needs() -> None:
    """`make initial-setup` replaced the tasks, so it carries the same guarantees."""
    makefile = (ROOT / "template" / "Makefile.jinja").read_text()

    target = makefile[makefile.index("initial-setup:") : makefile.index("run:")]

    # Every step that writes checks first, so a second run changes nothing.
    assert "[ -d .git ] || git init" in target
    assert "git remote get-url origin" in target and "git remote add origin" in target
    assert "[ -f uv.lock ] || uv lock" in target
    assert "git add ." in target
    assert "git rev-parse HEAD" in target and "commit -q -m" in target


def test_the_scaffold_commit_is_attributed_to_the_author() -> None:
    """A fresh feedstock has no git config of its own to fall back on."""
    makefile = (ROOT / "template" / "Makefile.jinja").read_text()

    assert 'user.name="{{ author }}"' in makefile
    assert 'user.email="{{ author_email }}"' in makefile


def test_preview_question_defaults() -> None:
    """The SDK default is one exact version and extra volumes are opt-in."""
    assert re.fullmatch(
        r"\d+\.\d+\.\d+((a|b|rc)\d+)?", COPIER["bookshelf_sdk_version"]["default"]
    )
    assert COPIER["extra_recipes"]["default"] == []


@pytest.mark.parametrize(
    "names", [[], ["second-volume"], ["second-volume", "third-volume"]]
)
def test_extra_recipes_accepts_lists_of_volume_names(names: list[str]) -> None:
    """Each entry becomes a recipe filename and a distinct volume."""
    assert not rejection("extra_recipes", names)


@pytest.mark.parametrize(
    "names",
    ["second-volume", {}, ["../escape"], ["Upper"], ["same", "same"], ["example"], [1]],
)
def test_extra_recipes_rejects_invalid_names(names: object) -> None:
    """Invalid paths and duplicate volumes cannot enter the caller."""
    assert rejection("extra_recipes", names)
