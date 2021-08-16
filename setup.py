from setuptools import setup

with open("README.rst", "r") as fh:
    long_description = fh.read()

setup(
    name='onefuse',
    version='1.3.0.1',
    description='OneFuse upstream provider package for Python',
    url='https://github.com/CloudBoltSoftware/onefuse-python-module',
    author='Mike Bombard',
    author_email='mbombard@cloudbolt.io',
    long_description=long_description,
    long_description_content_type="text/x-rst",
    packages=['onefuse'],
    install_requires=['requests', 'urllib3'],
    license="",

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
    ],
)
