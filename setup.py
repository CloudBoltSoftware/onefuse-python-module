from setuptools import setup

with open("README.rst", "r") as fh:
    long_description = fh.read()

setup(
    name='onefuse',
    version='2023.1.1',
    author='Cloudbolt Software, Inc.',
    author_email='support@cloudbolt.io',
    description='OneFuse upstream provider package for Python',
    url='https://github.com/CloudBoltSoftware/onefuse-python-module',
    long_description=long_description,
    long_description_content_type="text/x-rst",
    packages=['onefuse'],
    install_requires=['requests', 'urllib3', 'packaging'],
    license='Mozilla Public License 2.0 (MPL 2.0)',

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
    ],
)
