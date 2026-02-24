# HelmPush

Action GitHub réutilisable (Docker, Python 3.12) qui installe Helm et pousse un chart vers un registry OCI (ex. AWS ECR) ou un registry classique (username/password).

## Fonctionnalités

- **Docker + Python 3.12** : image légère avec Helm préinstallé
- **Deux modes d’auth** : ECR OCI (token) ou registry classique (username/password)
- **Chart** : répertoire ou archive `.tgz` — si c’est un répertoire, l’action fait `helm package` puis push
- **HTTP** : option `plain-http` pour les registries sans TLS (ex. Harbor en CI)

## Inputs

| Input | Requis | Défaut | Description |
|-------|--------|--------|--------------|
| `registry-url` | Oui | — | URL du registry, ex. `oci://123456789123.dkr.ecr.eu-west-1.amazonaws.com` ou `https://h.cfcr.io/org/repo` |
| `username` | Non | `AWS` (si token) | Utilisateur (ECR ou registry classique) |
| `password` | Non | — | Mot de passe (registry classique) |
| `access-token` | Non | — | Token ECR (ex. sortie de `aws ecr get-login-password`) |
| `chart-folder` | Non | `chart` | Chemin du chart (répertoire ou fichier `.tgz`) relatif au workspace |
| `force` | Non | `false` | Force le push (écrasement si le registry le permet) |
| `plain-http` | Non | `false` | Utilise HTTP sans TLS (Harbor en CI, etc.) |

**Règle** : si `access-token` est fourni → mode ECR (username optionnel, défaut `AWS`). Sinon → `username` et `password` obligatoires.

## Outputs

| Output | Description |
|--------|-------------|
| `push-status` | `success` en cas de push réussi |

## Utilisation

### ECR OCI

```yaml
- name: Login ECR
  id: ecr_login
  run: |
    echo "result=$(aws ecr get-login-password --region eu-west-1)" >> $GITHUB_OUTPUT

- name: Push Helm chart vers ECR
  uses: votre-org/HelmPush@v1
  with:
    registry-url: oci://123456789123.dkr.ecr.eu-west-1.amazonaws.com
    username: AWS
    access-token: ${{ steps.ecr_login.outputs.result }}
    chart-folder: chart
```

### Registry classique (username / password)

```yaml
- name: Push Helm chart
  uses: votre-org/HelmPush@v1
  with:
    username: ${{ secrets.HELM_USERNAME }}
    password: ${{ secrets.HELM_PASSWORD }}
    registry-url: 'https://h.cfcr.io/org/repo'
    chart-folder: chart
    force: true
```

### Harbor (ou autre registry HTTP, ex. CI)

Pour un registry en HTTP sans TLS, utilisez `plain-http: true` :

```yaml
- name: Push Helm chart vers Harbor
  uses: votre-org/HelmPush@v1
  with:
    registry-url: oci://votre-harbor/helm-e2e
    username: admin
    password: ${{ secrets.HARBOR_PASSWORD }}
    chart-folder: chart
    plain-http: true
```

## Format du chart

- **Répertoire** : ex. `chart/` avec `Chart.yaml`, `values.yaml`, `templates/`. L’action exécute `helm package` puis pousse l’archive générée.
- **Archive** : chemin vers un fichier `.tgz` déjà packagé (poussé tel quel).

## Développement et tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

Les tests mockent `helm` et couvrent : `get_input`, `get_registry_host`, login/push (ECR et classique), `force`, `plain-http`, erreurs (credentials manquants, échec login/push).

## E2E CI (Harbor)

Le workflow [.github/workflows/e2e-harbor.yml](.github/workflows/e2e-harbor.yml) lance un E2E sur push/PR vers `main` :

1. Configure Docker (registry insecure pour le host)
2. Télécharge et configure Harbor (HTTP), le démarre
3. Attend que l’API Harbor soit prête
4. Crée le projet `helm-e2e` via l’API
5. Vérifie le registry avec `docker login`
6. **Utilise cette action** pour pousser le chart [chart/](chart/) vers Harbor (`plain-http: true`)
7. Vérifie la présence du manifest OCI dans Harbor

Le dossier [chart/](chart/) est un chart minimal utilisé pour ce test E2E.
