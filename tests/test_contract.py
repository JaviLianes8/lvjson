import importlib.resources
import re
from pathlib import Path

import lvjson

_ROOT = Path(__file__).resolve().parents[1]

# The public API. Add every exported name here as the library grows; this list is the
# contract and the test below fails if the module and this list disagree.
PUBLIC_API: list[str] = [
    "InfSpelling",
    "LVJSONError",
    "NanInf",
    "NumberStyle",
    "count_nonfinite",
    "dumps",
    "has_nonfinite",
    "loads",
    "round_trip",
    "to_labview",
    "to_portable",
]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(lvjson.__all__) == sorted(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in lvjson.__all__:
        assert hasattr(lvjson, name)


def test_version_is_a_three_part_string() -> None:
    parts = lvjson.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def _pyproject() -> str:
    return (_ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_version_matches_pyproject_and_changelog() -> None:
    assert re.search(rf'^version = "{re.escape(lvjson.__version__)}"$', _pyproject(), re.M)
    changelog = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{lvjson.__version__}]" in changelog


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("lvjson").joinpath("py.typed").is_file()


def test_package_has_no_runtime_dependencies() -> None:
    assert re.search(r"^dependencies = \[\]$", _pyproject(), re.M)


def test_source_files_stay_short() -> None:
    for path in (_ROOT / "src" / "lvjson").glob("*.py"):
        lines = path.read_text(encoding="utf-8").count("\n")
        assert lines <= 200, f"{path.name} has {lines} lines"


def test_readme_examples_run() -> None:
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)```", readme, re.DOTALL)
    assert blocks, "the README has no python examples"
    for block in blocks:
        exec(compile(block, "README.md", "exec"), {})
