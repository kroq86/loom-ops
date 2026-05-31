# Publishing `loom-ops` to PyPI

Workflow: [`.github/workflows/publish.yml`](../.github/workflows/publish.yml) runs on **GitHub Release** (tag `v*` matching `pyproject.toml` version) or **workflow_dispatch**.

## 1. Repository secret (recommended)

1. Create a PyPI API token: [pypi.org/manage/account/token](https://pypi.org/manage/account/token/) with upload scope for project **`loom-ops`** (or entire account for all Loom packages).
2. In GitHub: **Settings → Secrets and variables → Actions → New repository secret**
3. Name: `PYPI_API_TOKEN`, value: the token (including `pypi-` prefix).
4. Re-run the failed **Publish to PyPI** workflow for tag [v0.2.0](https://github.com/kroq86/loom-ops/releases/tag/v0.2.0), or create a new patch release after bumping version.

The same secret value is used in `loom-runner`, `loom-tailcalls`, and `flow-xray` — copy it to `loom-ops` and `loom-run` if those repos lack the secret.

## 2. Trusted publishing (optional)

On PyPI → **Publishing** → **Add a new pending publisher**:

- Owner: `kroq86`
- Repository: `loom-ops`
- Workflow: `publish.yml`
- Environment: (empty unless you use GitHub Environments)

Then switch the workflow to OIDC (`id-token: write`, `pypa/gh-action-pypi-publish`). Only use one method (token **or** OIDC) per repo.

## Verify

```bash
pip install "loom-ops[api,telegram]"
loom-ops --help
```

Badge in README should show the published version once upload succeeds.
