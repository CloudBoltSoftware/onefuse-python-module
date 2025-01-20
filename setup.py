import os
import shutil
import subprocess
import logging

# Set up logging configuration
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def get_setuptools_location():
    try:
        # Get the location of setuptools.
        result = subprocess.run(
            ['pip', 'show', 'setuptools'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True
        )

        # If pip show failedd.
        if result.returncode != 0:
            log.error("Error: pip show setuptools failed.")
            return None

        # Extract the location of setuptools.
        location = None
        for line in result.stdout.splitlines():
            if line.startswith('Location:'):
                location = line.split(':')[1].strip()

        if not location:
            log.error("Error: Could not extract location of setuptools.")
            return None

        return location

    except Exception as e:
        log.error(f"Error extracting setuptools location: {e}")
        return None


target_directory = get_setuptools_location()

if target_directory:
    # Construct the full path for the build.py.
    build_file_path = os.path.join(target_directory, 'setuptools/command', 'build.py')

    try:
        # Check if the build.py file already exists at the target location
        if not os.path.exists(build_file_path):
            shutil.copy('build.py', build_file_path)
            print(f"build.py has been copied to {build_file_path}")
        else:
            print(f"build.py already exists at {build_file_path}, skipping creation.")
    except FileNotFoundError as e:
        print(f"Error: The file 'build.py' was not found in the current directory. {e}")
    except Exception as e:
        print(f"An error occurred while copying the file: {e}")

else:
    print("Could not determine teh setuptools location. Skipping build.py creation.")

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
