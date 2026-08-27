from setuptools import setup, find_packages

setup(
    name='pyharp',
    version='0.3.1',
    url='https://github.com/TEAMuP-dev/pyharp',
    author='TEAMuP',
    author_email='fcwitkow@ur.rochester.edu',
    description='',
    packages=find_packages(),
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
    ]
)
