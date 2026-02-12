# Release Instructions

## Creating a Release

1. **Update changelog** (if applicable)

2. **Create and push a tag**
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

3. **Create GitHub Release**
   - Go to https://github.com/happyskygang/yeelowoon/releases
   - Click "Create a new release"
   - Select the tag (e.g., `v0.1.0`)
   - Add release notes
   - Click "Publish release"

4. **Automatic publishing**
   - The `publish.yml` workflow triggers on release
   - Package is built and published to PyPI

## PyPI Trusted Publishing Setup

To enable automatic publishing without API tokens:

1. **Go to PyPI** → Your Projects → `drum2midi` → Settings → Publishing

2. **Add a new publisher**:
   | Field | Value |
   |-------|-------|
   | Owner | `happyskygang` |
   | Repository | `yeelowoon` |
   | Workflow name | `publish.yml` |
   | Environment | `pypi` |

3. **Create GitHub Environment**:
   - Go to repo Settings → Environments
   - Create environment named `pypi`
   - (Optional) Add protection rules

## Fallback: PyPI API Token

If Trusted Publishing is not available:

1. **Create PyPI API token**:
   - Go to https://pypi.org/manage/account/token/
   - Create token scoped to `drum2midi` project

2. **Add GitHub Secret**:
   - Go to repo Settings → Secrets → Actions
   - Add secret `PYPI_API_TOKEN` with the token value

3. **Modify workflow** to use token:
   ```yaml
   - name: Publish to PyPI
     uses: pypa/gh-action-pypi-publish@release/v1
     with:
       password: ${{ secrets.PYPI_API_TOKEN }}
   ```

## Version Scheme

This project uses `setuptools_scm` for automatic versioning:

- Tagged commits: `v1.0.0` → version `1.0.0`
- Untagged commits: `1.0.0.dev1+gXXXXXXX`
- Local builds: version derived from latest tag + commit count

## Local Build Test

```bash
pip install build
python -m build
ls dist/
```
