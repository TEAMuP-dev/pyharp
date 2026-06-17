from setuptools import setup, find_packages

setup(
    name='pyharp',
    version='0.3.0',
    url='https://github.com/TEAMuP-dev/pyharp',
    author='Frank Cwitkowitz, Christodoulos Benetatos, Hugo Flores García, Patrick O\'Reilly, Nathan Pruyne, Aldo Aguilar and Saumya Pailwan',
    author_email='fcwitkow@ur.rochester.edu',
    description='',
    packages=find_packages(),
    install_requires=[
        'gradio>=6.17.3,<7',
        'descript-audiotools',
        'symusic'
    ]
)
