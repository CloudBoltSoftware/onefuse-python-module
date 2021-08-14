from setuptools import setup

setup(
    name='onefuse',
    version='1.3.0',
    description='OneFuse upstream provider package for Python',
    url='https://github.com/CloudBoltSoftware/onefuse-python-module',
    author='Mike Bombard',
    author_email='mbombard@cloudbolt.io',
    packages=['onefuse'],
    install_requires=['requests', 'urllib3'],

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
    ],
)
