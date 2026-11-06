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
BRAND_DIR = REPO_ROOT / "custom_components" / "comfoclime" / "brand"
# Source of truth: homeassistant/generated/integration_categories.json in core.
EXPECTED_CATEGORIES = [
    "climate.heat_pumps_air_conditioning",
    "climate.fans_ventilation",
]
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
    # aiohttp ships with Home Assistant itself; hassfest rejects it in custom manifests.
    assert manifest["requirements"] == ["pydantic>=2.0.0"]


def test_manifest_declares_marketplace_categories() -> None:
    categories = _read_manifest()["categories"]

    assert categories == EXPECTED_CATEGORIES
    assert 1 <= len(categories) <= 3
    assert len(set(categories)) == len(categories)
    # Hassfest rejects a parent category next to one of its own subcategories.
    assert not {c.partition(".")[0] for c in categories if "." in c} & set(categories)


def _png_size(path: Path) -> tuple[int, int]:
    """Read width/height from the PNG IHDR chunk (no image library needed)."""
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n", path.name
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def test_brand_images_exist_in_integration_brand_folder() -> None:
    # Sizes per the HA brand image rules: icon 256x256 (512x512 @2x); logo's
    # shortest side 128-256 px (256-512 px @2x).
    assert _png_size(BRAND_DIR / "icon.png") == (256, 256)
    assert _png_size(BRAND_DIR / "icon@2x.png") == (512, 512)
    assert 128 <= min(_png_size(BRAND_DIR / "logo.png")) <= 256
    assert 256 <= min(_png_size(BRAND_DIR / "logo@2x.png")) <= 512
    assert not (REPO_ROOT / "custom_components" / "comfoclime" / "icons").exists()


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


def test_hacs_does_not_force_release_zip_install() -> None:
    hacs = _read_hacs()

    assert "zip_release" not in hacs
    assert "filename" not in hacs


def test_python_and_ruff_targets_are_aligned() -> None:
    """ruff's target-version must track requires-python's major.minor.

    The patch component matters too - Home Assistant 2026.3+ requires 3.14.2
    specifically - but ruff targets only major.minor, so it is ignored here.
    """
    pyproject = _read_pyproject()

    requires_python = pyproject["project"]["requires-python"]
    match = re.fullmatch(r">=(\d+)\.(\d+)(?:\.\d+)?", requires_python)

    assert match is not None, f"unexpected requires-python format: {requires_python}"
    assert pyproject["tool"]["ruff"]["target-version"] == f"py{match.group(1)}{match.group(2)}"


def test_release_zip_contains_hacs_integration_path() -> None:
    workflow = _read_release_workflow()

    assert "zip -r comfoclime.zip custom_components/comfoclime/" in workflow
