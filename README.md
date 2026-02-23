# HelmPush

Reusable GitHub Action (Docker, Python 3.12) that installs Helm and pushes a chart to an OCI registry (e.g. AWS ECR) or a classic registry (username/password).

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `registry-url` | yes | e.g. `oci://123456789123.dkr.ecr.eu-west-1.amazonaws.com` or `https://h.cfcr.io/user_or_org/reponame` |
| `username` | no | Registry username (for ECR with token, defaults to `AWS`) |
| `password` | no | Registry password (for classic registry) |
| `access-token` | no | ECR token (e.g. from `steps.ecr_login.outputs.result`) |
| `chart-folder` | no | Path to chart directory (default: `chart`) |
| `force` | no | Force push (default: `false`) |

## Usage

### ECR OCI

```yaml
- name: Login to ECR
  id: ecr_login
  # ... step that outputs the ECR token (e.g. aws ecr get-login-password)

- name: Push Helm chart to ECR
  uses: your-org/HelmPush@v1
  with:
    registry-url: oci://123456789123.dkr.ecr.eu-west-1.amazonaws.com
    username: AWS
    access-token: ${{ steps.ecr_login.outputs.result }}
    chart-folder: chart
```

### Classic registry (username/password)

```yaml
- name: Push Helm chart
  uses: your-org/HelmPush@v1
  with:
    username: ${{ secrets.HELM_USERNAME }}
    password: ${{ secrets.HELM_PASSWORD }}
    registry-url: 'https://h.cfcr.io/user_or_org/reponame'
    force: true
    chart-folder: chart
```

## Outputs

- `push-status`: `success` when the push completes successfully.

## Development and tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

Tests cover: `get_input`, `get_registry_host`, and `main()` (login and push) with mocked `helm` subprocess calls—ECR vs classic mode, force flag, missing inputs, and login/push failures.

## E2E CI (Harbor)

The workflow [.github/workflows/e2e-harbor.yml](.github/workflows/e2e-harbor.yml) runs on push/PR to `main`/`master`:

1. Configures Docker for insecure localhost registry and installs Docker Compose
2. Downloads and configures Harbor (HTTP, localhost), then starts it
3. Waits for Harbor API health
4. Creates project `helm-e2e` via API
5. **Docker login** to Harbor (`admin` / `Harbor12345`) to verify the registry
6. Installs Helm, runs **helm registry login** and **helm push** of the [chart/](chart/) to `oci://localhost/helm-e2e`
7. Verifies with **helm pull** and checks `Chart.yaml`

The [chart/](chart/) directory is a minimal Helm chart used for this E2E test.
