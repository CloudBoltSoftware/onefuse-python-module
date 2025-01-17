import sys
import subprocess
import logging


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def get_setuptools_version():
    try:
        # Run pip show setuptools and capture the output
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "setuptools"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Extract the version from the output
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                version = line.split(":")[1].strip()
                return version
        return None
    except subprocess.CalledProcessError:
        return None


def ensure_setuptools():
    setuptools_version = get_setuptools_version()

    if setuptools_version == "75.6.0":
        log.info(
            f"setuptools version {setuptools_version} detected. Reinstalling it to resolve the dependecies"
        )

        # Run pip install --force-reinstall for version 75.6.0
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--force-reinstall",
                "setuptools==75.6.0",
            ]
        )
        log.info("setuptools 75.6.0 reinstalled successfully.")
    elif setuptools_version:
        log.info(f"setuptools version {setuptools_version} is up-to-date.")
    else:
        log.info("setuptools not found. Installing version 75.6.0...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "setuptools==75.6.0"]
        )


ensure_setuptools()

from setuptools import setup

with open("README.rst", "r") as fh:
    long_description = fh.read()

setup(
    name='onefuse',
    version='2025.1.2',
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
