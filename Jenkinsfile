pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    parameters {
        string(
            name: 'DOCKERHUB_REPO',
            defaultValue: 'lostchampion/deployscope',
            description: 'Docker Hub repository, for example student/deployscope'
        )
        string(
            name: 'KUBERNETES_NAMESPACE',
            defaultValue: 'default',
            description: 'Namespace already accessible to this Jenkins agent'
        )
    }

    environment {
        APP_VERSION = "1.0.${BUILD_NUMBER}"
        IMAGE_TAG = ''
        IMAGE = ''
    }

    stages {
       
    stage('Checkout') {
        steps {
            checkout scm
            script {
                def commitSha = sh(
                    script: 'git rev-parse HEAD',
                    returnStdout: true
                ).trim()

            env.IMAGE_TAG = commitSha
            env.IMAGE = "docker.io/${params.DOCKERHUB_REPO}:${commitSha}"

            echo "Using immutable image tag: ${commitSha}"
        }
    }
}


        stage('Build and Test') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    python -m pip install --upgrade pip
                    python -m pip install -r requirements-dev.txt
                    python -m pytest
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    docker build \
                      --build-arg APP_VERSION="${APP_VERSION}" \
                      --build-arg BUILD_NUMBER="${BUILD_NUMBER}" \
                      --build-arg GIT_COMMIT="${IMAGE_TAG}" \
                      --build-arg REPOSITORY_URL="${GIT_URL}" \
                      --tag "${IMAGE}" .
                '''
            }
        }

        stage('Push Image') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKERHUB_USERNAME',
                    passwordVariable: 'DOCKERHUB_PASSWORD'
                )]) {
                    sh '''
                        printf '%s' "$DOCKERHUB_PASSWORD" \
                          | docker login --username "$DOCKERHUB_USERNAME" --password-stdin
                        docker push "${IMAGE}"
                        docker logout
                    '''
                }
            }
        }

        stage('Deploy to Minikube') {
            steps {
                sh '''
                    kubectl apply --namespace "${KUBERNETES_NAMESPACE}" -f k8s/
                    kubectl set image \
                      --namespace "${KUBERNETES_NAMESPACE}" \
                      deployment/deployscope deployscope="${IMAGE}"
                    kubectl set env \
                      --namespace "${KUBERNETES_NAMESPACE}" \
                      deployment/deployscope \
                      APP_VERSION="${APP_VERSION}" \
                      BUILD_NUMBER="${BUILD_NUMBER}" \
                      GIT_COMMIT="${IMAGE_TAG}" \
                      REPOSITORY_URL="${GIT_URL}"
                '''
            }
        }

        stage('Verify Deployment') {
            steps {
                sh '''
                    kubectl rollout status \
                      --namespace "${KUBERNETES_NAMESPACE}" \
                      deployment/deployscope --timeout=180s

                    PORT_FORWARD_LOG="$(mktemp)"
                    kubectl port-forward \
                      --namespace "${KUBERNETES_NAMESPACE}" \
                      service/deployscope 5000:5000 >"$PORT_FORWARD_LOG" 2>&1 &
                    PORT_FORWARD_PID=$!
                    trap 'kill "$PORT_FORWARD_PID" 2>/dev/null || true; rm -f "$PORT_FORWARD_LOG"' EXIT

                    for attempt in $(seq 1 20); do
                      if curl --fail --silent http://127.0.0.1:5000/health; then
                        printf '\\n'
                        exit 0
                      fi
                      sleep 2
                    done
                    cat "$PORT_FORWARD_LOG"
                    echo "Health check failed after rollout."
                    exit 1
                '''
            }
        }
    }

    post {
        always {
            sh 'docker logout >/dev/null 2>&1 || true'
            cleanWs()
        }
    }
}
