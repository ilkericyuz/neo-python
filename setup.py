#!/usr/bin/env python3
"""The setup script."""

from setuptools import setup, find_packages
try:  # pip version >= 10.0
    from pip._internal.req import parse_requirements
    from pip._internal.download import PipSession
except ImportError:  # pip version < 10.0
    from pip.req import parse_requirements
    from pip.download import PipSession


with open('README.rst') as readme_file:
    readme = readme_file.read()

# get the requirements from requirements.txt
install_reqs = parse_requirements('requirements.txt', session=PipSession())
reqs = [str(ir.req) for ir in install_reqs]

setup(
    name='neo-python',
    python_requires='>=3.6',
    version='0.8.4-dev',
    description="Python Node and SDK for the NEO blockchain",
    long_description=readme,
    author="Thomas Saunders",
    author_email='tom@cityofzion.io',
    maintainer="Erik van den Brink",
    maintainer_email='erik@cityofzion.io',
    url='https://github.com/CityOfZion/neo-python',
    packages=find_packages(include=['neo']),
    entry_points = {
        'console_scripts': [
            'np-prompt=neo.bin.prompt:main',
            'np-api-server=neo.bin.api_server:main',
            'np-bootstrap=neo.bin.bootstrap:main',
            'np-reencrypt-wallet=neo.bin.reencrypt_wallet:main',
            'np-sign=neo.bin.sign_message:main',
            'np-export=neo.bin.export_blocks:main',
            'np-import=neo.bin.import_blocks:main',
        ],
    },
    include_package_data=True,
    install_requires=reqs,
    license="MIT license",
    zip_safe=False,
    keywords='neo, python, node',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)
