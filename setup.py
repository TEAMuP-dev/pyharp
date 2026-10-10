from pathlib import Path
from setuptools import setup, find_packages

import re


# Taken from the package rather than imported, which would need its dependencies first
INIT = Path(__file__).parent / 'pyharp' / '__init__.py'
DECLARATION = re.search(
    r'^__version__\s*=\s*[\'"]([^\'"]+)[\'"]',
    INIT.read_text(encoding='utf-8'),
    re.MULTILINE
)

if DECLARATION is None:
    raise RuntimeError(f'{INIT} declares no __version__ for setup.py to read.')

VERSION = DECLARATION.group(1)

setup(
    name='pyharp',
    version=VERSION,
    url='https://github.com/TEAMuP-dev/pyharp',
    author='TEAMuP',
    author_email='fcwitkow@ur.rochester.edu',
    description='A lightweight API for building HARP-compatible Gradio apps.',
    packages=find_packages(),
    # Model taxonomy, shared with HARP (see pyharp/tags.py)
    package_data={'pyharp': ['taxonomy.json']},
    # The Gradio version below requires 3.10 or newer
    python_requires='>=3.10',
    install_requires=[
        # Gradio >= 6.13 is required for HARP to receive error details: earlier
        # versions discard the error payload on the /gradio_api/call endpoint and
        # send a bare "data: null", which HARP cannot tell apart from a GPU quota
        # rejection (see TEAMuP-dev/HARP#349).
        'gradio>=6.13.0,<7',
        'descript-audiotools',
        # symusic 0.6.0 broke Synthesizer.render(): it raises "Unable to convert
        # function return value to a Python type" for its Eigen array return,
        # which breaks the MIDI synthesizer example. Score loading, note access,
        # tempos, and dump_midi are all unaffected, so this pin only matters for
        # synthesis. Verified working on 0.5.9 against both numpy 1.26 and 2.5;
        # unpin once it is fixed upstream.
        'symusic>=0.5.7,<0.6'
    ],
    extras_require={
        # Run with "pytest tests" from the repository root. packaging is a transitive
        # dependency of gradio, but the tests read it directly, so it is declared here.
        'test': ['pytest', 'packaging']
    }
)
