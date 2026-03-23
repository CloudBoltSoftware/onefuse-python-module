# Publishing Guide

## 1. Install and Setup pyenv with Python 3.12.10

### Install pyenv

**macOS (Homebrew):**
```bash
brew install pyenv
```

**Linux:**
```bash
curl https://pyenv.run | bash
```

Add the following to your shell config (`~/.zshrc` or `~/.bashrc`):
```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
```

Reload your shell:
```bash
source ~/.zshrc   # or source ~/.bashrc
```

### Install Python 3.12.10

```bash
pyenv install 3.12.10
```

### Create a Virtual Environment

```bash
pyenv shell 3.12.10
python -m venv .venv
source .venv/bin/activate
```

Confirm the Python version:
```bash
python --version
# Python 3.12.10
```

---

## 2. Install Required Packages

With the virtual environment active:

```bash
pip install --upgrade pip
pip install build twine
```

---

## 3. Bump the Version

Before every release, update the version in **two places** so they stay in sync.

**`pyproject.toml`:**
```toml
[project]
name = "onefuse"
version = "2026.2.0"   # <-- update this
```

**`onefuse/__init__.py`:**
```python
__version__ = "2026.2.0"   # <-- update this to match
```

The version scheme used in this project is `YYYY.MINOR.PATCH` (e.g. `2026.1.0`, `2026.1.1`, `2026.2.0`).

> **Note:** PyPI does not allow re-uploading the same version. Always bump before building.

---

## 4. Build and Publish to TestPyPI

Use TestPyPI to verify the package before publishing to the real index.

### Create a TestPyPI Account

1. Register at [https://test.pypi.org](https://test.pypi.org)
2. Go to **Account Settings → API tokens**
3. Create a token scoped to **Entire account**

### Store Credentials (optional)

Add the following to `~/.pypirc` to avoid being prompted each time:
```ini
[testpypi]
username = __token__
password = pypi-your-testpypi-token-here
```

### Build

```bash
rm -rf dist/
python -m build
```

### Validate

```bash
twine check dist/*
```

### Upload to TestPyPI

```bash
twine upload --repository testpypi dist/*
```

When prompted:
- **Username:** `__token__`
- **Password:** your TestPyPI API token

### Install from TestPyPI

```bash
pip install --index-url https://test.pypi.org/simple/ onefuse
```

Verify the installed version:
```bash
python -c "import onefuse; print(onefuse.__version__)"
```

---

## 4. Build and Publish to PyPI

Only proceed here after successfully verifying the package on TestPyPI.

### Create a PyPI Account

1. Register at [https://pypi.org](https://pypi.org)
2. Go to **Account Settings → API tokens**
3. Create a token scoped to **Entire account** (or to the `onefuse` project once it exists)

### Store Credentials (optional)

Add the following to `~/.pypirc`:
```ini
[pypi]
username = __token__
password = pypi-your-pypi-token-here
```

### Build

```bash
rm -rf dist/
python -m build
```

### Validate

```bash
twine check dist/*
```

### Upload to PyPI

```bash
twine upload dist/*
```

When prompted:
- **Username:** `__token__`
- **Password:** your PyPI API token

### Install from PyPI

```bash
pip install onefuse
```

Verify the installed version:
```bash
python -c "import onefuse; print(onefuse.__version__)"
```

---

> **Note:** PyPI does not allow re-uploading the same version. If a release needs to be corrected after uploading, bump the version in `pyproject.toml` and `onefuse/__init__.py` before building and uploading again.
