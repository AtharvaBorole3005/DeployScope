# DeployScope

DeployScope is a compact Flask status page and student demonstration project for a CI/CD pipeline. The intended flow is GitHub → Jenkins → Docker Hub → Kubernetes on Minikube. The app reports build metadata supplied by its environment, but it does not invent pipeline runs, release history, or deployment success.

## Architecture

1. A GitHub change is checked out by Jenkins.
2. Jenkins installs development dependencies and runs pytest.
3. Jenkins builds a Docker image tagged with the full Git commit SHA.
4. Jenkins authenticates to Docker Hub through a Jenkins credential and pushes the image.
5. A Jenkins agent with Kubernetes access applies the manifests and updates the Deployment image and metadata.
6. Jenkins waits for rollout and checks `/health` through a temporary port-forward.

**Connectivity is not automatic:** an AWS-hosted Jenkins controller/agent does not inherently have access to Minikube running on a student laptop. The agent executing the deploy stages must have Docker, `kubectl`, and Minikube-cluster credentials/network connectivity to the same reachable cluster. Use a deliberately configured, secured agent; do not expose an unauthenticated Kubernetes API or Minikube to the public internet. The pipeline does not provision AWS resources or a cluster.

## Project structure

```text
DeployScope/
├── app.py
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── tests/test_app.py
├── templates/index.html
├── static/style.css
├── static/script.js
├── Dockerfile
├── .dockerignore
├── .gitignore
├── Jenkinsfile
└── k8s/
    ├── deployment.yaml
    └── service.yaml
```

## Prerequisites

- Python 3.10 or newer and Git
- Docker Desktop (Windows) or Docker Engine
- A GitHub repository (created and managed manually)
- A Docker Hub account and repository
- Jenkins with a Linux agent, Docker access, and the required Kubernetes/Minikube access
- `kubectl` and Minikube for local Kubernetes work

### Windows PowerShell: local setup

From the project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

If PowerShell blocks activation, either use a permitted execution policy for your user or invoke the environment directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Run and test locally

Run the tests:

```powershell
python -m pytest
```

Start the Flask development server (for local demonstration only):

```powershell
python app.py
```

Open `http://127.0.0.1:5000/`. Check health at `http://127.0.0.1:5000/health` and metadata at `http://127.0.0.1:5000/api/version`.

The default values are explicitly local: version `0.1.0-local`, build `local-development`, commit `unknown`, and repository `Not configured (local development)`. Deployment status is `Unavailable` unless a real reporting integration is built; this application intentionally does not infer success from being online. Release history is empty until a genuine history source is connected.

Set metadata in a PowerShell session before starting the app if needed:

```powershell
$env:APP_VERSION = "1.0.0"
$env:BUILD_NUMBER = "local-demo"
$env:GIT_COMMIT = "your-commit-sha"
$env:REPOSITORY_URL = "https://github.com/your-account/deployscope"
python app.py
```

Unset the values when done with `Remove-Item Env:APP_VERSION`, and similarly for the other variables. Do not put credentials in these variables.

## Docker

Build a local image (no image is published by this command):

```powershell
docker build -t deployscope:local .
```

Run it:

```powershell
docker run --rm -p 5000:5000 deployscope:local
```

Visit `http://localhost:5000/`. The image uses the official Python slim base image, Gunicorn, and a non-root runtime user. Build arguments can provide the four metadata values; never pass credentials as build arguments or bake them into an image.

## GitHub setup

Create an empty repository on GitHub, then connect this local folder. These commands do not push anything:

```powershell
git init
git add .
git commit -m "Create DeployScope CI/CD project"
git branch -M main
git remote add origin https://github.com/your-account/deployscope.git
```

Review the repository and remote before manually choosing whether to push. No GitHub action, push, or remote configuration is performed automatically by this project.

## Docker Hub setup

1. Create a Docker Hub repository, for example `your-account/deployscope`.
2. In Jenkins, create a **Username with password** credential with ID `dockerhub-creds`.
3. Use a Docker Hub access token as the credential password where possible. Never put the token in the Jenkinsfile, source, shell history, or image.
4. Set the Jenkins build parameter `DOCKERHUB_REPO` to the repository name. The example value is only a placeholder.

The Jenkinsfile uses `docker login --password-stdin` and pushes an immutable tag equal to the full checked-out commit SHA.

## Jenkins on AWS

Install Jenkins on an AWS Linux host/agent appropriate for the class environment. The pipeline expects:

- Pipeline, Git, Credentials Binding, and Workspace Cleanup plugins. Install the suggested Pipeline dependencies; Workspace Cleanup provides `cleanWs()`.
- A Linux agent with Git, Python 3, `venv`, Docker CLI/daemon access, `curl`, `kubectl`, and `minikube` installed as required by the configured deployment model.
- The `dockerhub-creds` username/password credential described above.
- A Jenkins job configured as **Pipeline script from SCM** and pointing at this repository's `Jenkinsfile`.
- `DOCKERHUB_REPO` and `KUBERNETES_NAMESPACE` parameters set appropriately.

**Minikube connectivity assumption:** the deploy and verify commands run on the Jenkins agent, not magically on your laptop. A Minikube cluster on a developer workstation is normally not reachable from AWS. For a classroom demo, use a secured agent that can intentionally reach the cluster, or run Jenkins/agent in an environment with Minikube access. Ensure the agent's kubeconfig context points at the intended cluster and the Jenkins OS user has permission to use Docker. Validate this connectivity before running the job. Do not open cluster credentials or an unauthenticated API to the internet.

## Minikube and kubectl

Install Minikube and `kubectl` using their official instructions for your OS. To create and start a local cluster manually:

```powershell
minikube start
kubectl config current-context
kubectl get nodes
```

The manifests use a NodePort service on port `30080`. Applying them manually requires changing the placeholder image in `k8s/deployment.yaml` to an image you have already built and made available to the cluster; no image is published automatically. The Jenkins pipeline applies the manifests, then replaces the placeholder with the commit-tagged image and injects metadata.

For manual local testing, build/load an image into Minikube (for example, use `minikube image build -t your-dockerhub-username/deployscope:local .`) and update the manifest image to that exact reference before applying:

```powershell
kubectl apply -f k8s/
kubectl rollout status deployment/deployscope
minikube service deployscope --url
```

Open the URL printed by Minikube. Verify `/health` and `/api/version`. A cluster started inside Docker Desktop or a VM may require its own image-loading/networking approach. The Jenkins health check uses `kubectl port-forward` from the agent and fails the job if rollout or health verification fails.

## Pipeline stages

| Stage | What it does |
| --- | --- |
| Checkout | Checks out SCM and derives the full commit SHA. |
| Build and Test | Creates a Python virtual environment and runs pytest. |
| Docker Build | Builds the image with the immutable commit tag and metadata. |
| Push Image | Logs in with `dockerhub-creds` and pushes that tag. |
| Deploy to Minikube | Applies Kubernetes resources, sets the image and metadata. |
| Verify Deployment | Waits for rollout and requests `/health` through a port-forward. |

`BUILD_NUMBER`, the application version, commit SHA, and repository URL are supplied to the image and Deployment. A successful Jenkins run is evidence of that run's rollout and health check; the app itself does not claim deployment status.

## Demonstrating a second change

1. Change a visible detail in `templates/index.html` or `static/style.css`.
2. Run `python -m pytest` locally.
3. Commit the change, then manually push it to the GitHub branch configured in Jenkins.
4. Run the Jenkins job again and capture the new build and commit-tagged image.
5. Confirm the rollout completed and the Jenkins health check passed.
6. Open the Minikube service URL, refresh the page, and verify the visible change and `/api/version` commit metadata.

## Screenshots for the assignment

Capture genuine screenshots of:

1. The responsive DeployScope home page with its current metadata and honest empty release state.
2. The Jenkins console showing all six real pipeline stages for a completed run.
3. Docker Hub showing the commit-SHA image tag, only after the pipeline really pushes it.
4. `kubectl get deployments,pods,services` and the app opened from the Minikube service URL.
5. A second source change followed by a new Jenkins build and updated commit metadata.

Do not edit screenshots to imply successful stages, builds, pushes, or deployments that did not occur.

## Common errors

- **`pytest` or Flask is missing:** activate `.venv` and install `requirements-dev.txt`.
- **Docker daemon permission denied:** confirm Docker is running and the Jenkins agent user has Docker access; reconnect/restart the agent after permission changes.
- **Docker Hub unauthorized:** verify credential ID `dockerhub-creds`, token permissions, and exact repository name.
- **`ImagePullBackOff`:** verify the pushed image name/tag and repository visibility or configure a Kubernetes image pull secret for a private repository.
- **`kubectl` cannot connect:** check `kubectl config current-context`, kubeconfig ownership, network reachability, and that the Jenkins agent—not just the controller—can reach the cluster.
- **Minikube is unreachable from AWS:** this is a connectivity/architecture issue, not an application setting. Use a secured agent with deliberate cluster access; do not expose Minikube publicly.
- **Rollout times out:** inspect `kubectl describe deployment deployscope`, pod events, image availability, and probe logs.
- **Health check fails:** inspect pod readiness and `kubectl logs deployment/deployscope`; confirm port `5000` and `/health` are reachable.
- **`cleanWs` is unavailable:** install the Jenkins Workspace Cleanup plugin.
- **PowerShell refuses activation:** use the direct `.\.venv\Scripts\python.exe` command shown above or configure an allowed user-level policy.

## Cost and credential safety

AWS EC2, storage, data transfer, and related resources may incur charges. Review pricing, budgets, and class policies before creating AWS resources, and stop/delete resources when finished. This project creates no AWS resources, publishes no image, deploys nothing, and makes no Git push on its own. Keep AWS keys, GitHub tokens, Docker Hub tokens, kubeconfigs, and Jenkins secrets private; use Jenkins credentials and least privilege, and never commit secrets.
