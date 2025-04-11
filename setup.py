from setuptools import setup, find_packages

setup(
    name='pyharp',
    version='0.2.0',
    url='https://github.com/TEAMuP-dev/pyharp',
    author='Hugo Flores García, Christos Benetatos, Patrick O\'Reilly and Aldo Aguilar',
    author_email='hugofloresgarcia@u.northwestern.edu',
    description='',
    packages=find_packages(),
    install_requires=[
        'gradio==5.24.0',
        'descript-audiotools',
        'symusic'
    ]
)
