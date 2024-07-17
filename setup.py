from setuptools import setup, find_packages

setup(
    name='pyharp',
    version='0.1.1',
    url='https://github.com/audacitorch/pyharp',
    author='Hugo Flores García, Christos Benetatos, Patrick O\'Reilly and Aldo Aguilar',
    author_email='hugofloresgarcia@u.northwestern.edu',
    description='',
    packages=find_packages(),    
    install_requires=[
        'gradio==4.7.1',
        'descript-audiotools',
        'symusic'
    ]
)