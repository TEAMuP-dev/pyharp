"""
Tests for what pyharp declares and ships.

These guard the environment and the distribution rather than any behavior: a pin that
the installed packages no longer satisfy, or a data file missing from the package, both
fail somewhere far from the cause.
"""

import os
import sys
import types
from importlib import metadata

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SETUP = os.path.join(ROOT, "setup.py")


def declared():
    """
    The keyword arguments setup.py passes to setup().

    Read from the file rather than from installed metadata, which goes stale whenever the
    working tree moves ahead of the last install.

    setuptools is stubbed rather than imported, since a virtual environment need not have
    it: pip builds an editable install in an isolated environment of its own. This runs at
    collection time, so importing it would take down the whole suite where it is absent.
    """
    captured = {}

    stub = types.ModuleType("setuptools")
    stub.setup = lambda **kwargs: captured.update(kwargs)
    stub.find_packages = lambda *args, **kwargs: []

    original = sys.modules.get("setuptools")
    sys.modules["setuptools"] = stub

    try:
        with open(SETUP, encoding="utf-8") as handle:
            source = handle.read()

        exec(compile(source, SETUP, "exec"), {"__name__": "__main__", "__file__": SETUP})
    finally:
        if original is None:
            del sys.modules["setuptools"]
        else:
            sys.modules["setuptools"] = original

    return captured


@pytest.fixture(scope="module")
def setup_kwargs():
    return declared()


# --------------------------------------------------------------------------------
# What is declared
# --------------------------------------------------------------------------------


def test_the_version_is_declared_and_parseable(setup_kwargs):
    from packaging.version import Version

    assert Version(setup_kwargs["version"])


def test_gradio_is_pinned_above_the_version_that_forwards_errors(setup_kwargs):
    """
    Below 6.13 Gradio discards the error payload, so a failed job reaches HARP with no
    message. See the comment in setup.py.
    """
    from packaging.requirements import Requirement

    gradio = next(
        Requirement(r) for r in setup_kwargs["install_requires"]
        if Requirement(r).name == "gradio"
    )

    assert not gradio.specifier.contains("6.12.0")
    assert gradio.specifier.contains("6.24.0")


def test_the_declared_version_is_the_package_version(setup_kwargs):
    """setup.py reads it from the package, so a bump in one place covers both."""
    import pyharp

    assert setup_kwargs["version"] == pyharp.__version__


def test_the_taxonomy_ships_with_the_package(setup_kwargs):
    """tags.py reads it at import, so an install without it cannot even be imported."""
    assert "taxonomy.json" in setup_kwargs["package_data"]["pyharp"]
    assert os.path.exists(os.path.join(ROOT, "pyharp", "taxonomy.json"))


def test_the_taxonomy_sits_beside_the_module_that_reads_it():
    from pyharp import tags

    assert os.path.exists(os.path.join(os.path.dirname(tags.__file__), "taxonomy.json"))


# --------------------------------------------------------------------------------
# What is installed
# --------------------------------------------------------------------------------


@pytest.mark.parametrize("requirement", declared()["install_requires"])
def test_the_installed_version_satisfies_the_pin(requirement):
    """
    A dependency outside its declared range fails somewhere unrelated. symusic is the
    standing example: 0.6.0 broke Synthesizer.render(), which only shows up when the
    MIDI synthesizer example tries to render.
    """
    from packaging.requirements import Requirement

    parsed = Requirement(requirement)

    try:
        installed = metadata.version(parsed.name)
    except metadata.PackageNotFoundError:
        pytest.skip(f"{parsed.name} is not installed")

    assert parsed.specifier.contains(installed, prereleases=True), (
        f"{parsed.name} {installed} is installed, but pyharp declares "
        f"\"{requirement}\". Reinstall with \"pip install -e .\" to bring it in line."
    )
