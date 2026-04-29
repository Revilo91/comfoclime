"""Project metadata regression tests."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "custom_components" / "comfoclime" / "manifest.json"
HACS_PATH = REPO_ROOT / "hacs.json"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
RELEASE_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "release.yml"


def _read_manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _read_hacs() -> dict[str, object]:
    return json.loads(HACS_PATH.read_text(encoding="utf-8"))


def _read_pyproject() -> dict[str, object]:
    return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))


def _read_release_workflow() -> str:
    return RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8")


def test_manifest_and_pyproject_versions_match() -> None:
    manifest = _read_manifest()
    pyproject = _read_pyproject()

    assert manifest["version"] == pyproject["project"]["version"]


def test_manifest_uses_canonical_repository_urls() -> None:
    manifest = _read_manifest()

    assert manifest["documentation"] == "https://github.com/Revilo91/comfoclime"
    assert manifest["issue_tracker"] == "https://github.com/Revilo91/comfoclime/issues"


def test_manifest_contains_current_home_assistant_metadata() -> None:
    manifest = _read_manifest()

    assert manifest["integration_type"] == "hub"
    assert manifest["iot_class"] == "local_polling"
    assert manifest["requirements"] == ["aiohttp>=3.8.0", "pydantic>=2.0.0"]


def test_hacs_minimum_does_not_exceed_dev_home_assistant_version() -> None:
    hacs = _read_hacs()
    pyproject = _read_pyproject()

    homeassistant_requirement = next(
        requirement
        for requirement in pyproject["dependency-groups"]["dev"]
        if requirement.startswith("homeassistant>=")
    )
    minimum_version = Version(str(hacs["homeassistant"]))
    dev_version = Version(homeassistant_requirement.removeprefix("homeassistant>="))

    assert minimum_version <= dev_version


def test_python_and_ruff_targets_are_aligned() -> None:
    pyproject = _read_pyproject()

    requires_python = pyproject["project"]["requires-python"]
    match = re.fullmatch(r">=(\d+)\.(\d+)", requires_python)

    assert match is not None
    assert pyproject["tool"]["ruff"]["target-version"] == f"py{match.group(1)}{match.group(2)}"


def test_release_zip_contains_hacs_integration_path() -> None:
    workflow = _read_release_workflow()

    assert "zip -r comfoclime.zip custom_components/comfoclime/" in workflow
