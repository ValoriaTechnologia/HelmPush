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
