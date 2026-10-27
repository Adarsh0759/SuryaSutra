// Jenkins never builds the (heavy, ML-dependency-laden) backend image itself — it SSHes
// to the app EC2 instance and runs the build/deploy there, so the Jenkins box only
// needs git + an SSH client, not Docker or multiple GB of build dependencies. Set
// APP_HOST below to the app instance's public IP, and add an SSH credential in
// Jenkins (Manage Jenkins -> Credentials) with ID "suryasutra-deploy-key" holding the
// deploy private key.
pipeline {
    agent any

    environment {
        APP_HOST = '100.61.126.234'
        APP_USER = 'ec2-user'
        APP_DIR  = '/opt/suryasutra/repo'
        REPO_URL = 'https://github.com/Adarsh0759/SuryaSutra.git'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Deploy to app server') {
            steps {
                sshagent(credentials: ['suryasutra-deploy-key']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no ${APP_USER}@${APP_HOST} '
                            set -e
                            if [ ! -d ${APP_DIR} ]; then
                                git clone ${REPO_URL} ${APP_DIR}
                            fi
                            cd ${APP_DIR}
                            git fetch origin main
                            git reset --hard origin/main
                            docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
                            docker image prune -f
                        '
                    """
                }
            }
        }

        stage('Smoke test') {
            steps {
                sh "curl -sf --max-time 10 http://${APP_HOST}/api/health"
            }
        }
    }
}
