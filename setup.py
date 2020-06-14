from setuptools import setup, find_packages
from codecs import open
from os import path

__version__ = '1.0.0'

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# get the dependencies and installs
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    all_reqs = f.read().split('\n')

install_requires = [x.strip() for x in all_reqs if 'git+' not in x]
dependency_links = [
    x.strip().replace('git+', '') for x in all_reqs if x.startswith('git+')
]

setup(
    name='listener2_lm',
    version=__version__,
    description='Compiles language models for Listener v2',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/mcfletch/listener2_lm',
    download_url='https://github.com/mcfletch/listener2_lm/tarball/' + __version__,
    license='MPL-2.0',
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
    ],
    keywords='',
    packages=find_packages(exclude=[]),
    include_package_data=True,
    author='Mike C. Fletcher',
    install_requires=install_requires,
    dependency_links=dependency_links,
    author_email='mcfletch@vrplumber.com',
    entry_points={
        'console_scripts': ['listener-lm-rebuild=listener2_lm.ds_genlm:main',],
    },
)
