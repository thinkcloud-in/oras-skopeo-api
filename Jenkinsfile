pipeline {
    agent any

    environment {
        APP_NAME        = "devraq-oras-skopeo-api"
        IMAGE_TAG       = "1.0.0"

        WORKDIR         = "/home/admin-01/Desktop/rcv/oras-skopeo-api"
        TAR_DIR         = "/home/admin-01/Desktop/rcv/tar"
        TAR_FILE        = "devraq-oras-skopeo-api_${IMAGE_TAG}.tar"

        REMOTE_HOST     = "172.16.0.101"
        REMOTE_USER     = "root"
        REMOTE_TAR_DIR  = "/home/rcv/daas_installer/daas_tar"
        REMOTE_BASE_DIR = "/home/rcv/daas_installer/daas_v1/oras-skopeo-api"
        SCRIPT_DIR      = "/home/rcv/Desktop/scrpit"
        DEPLOY_SCRIPT   = "oras_skopeo_api.sh"
        SSH_KEY         = "/root/.ssh/id_ed25519"
    }

    stages {

        stage('Prepare Directories') {
            steps {
                sh 'mkdir -p ${TAR_DIR}'
            }
        }

        stage('Checkout Oras Skopeo Code') {
            steps {
                dir("${WORKDIR}") {
                    deleteDir()
                    git branch: 'main',
                        url: 'https://github.com/thinkcloud-in/oras-skopeo-api.git',
                        credentialsId: 'github_token'
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                dir("${WORKDIR}") {
                    sh '''
                        docker image prune -a -f
                        docker build -t ${APP_NAME}:${IMAGE_TAG} .
                    '''
                }
            }
        }

        stage('Save Docker Image as TAR') {
            steps {
                sh '''
                    docker save -o ${TAR_DIR}/${TAR_FILE} ${APP_NAME}:${IMAGE_TAG}
                    ls -lh ${TAR_DIR}
                '''
            }
        }

        stage('Copy TAR & YAMLs to Remote Server') {
            steps {
                sh """
                    # Create remote directories
                    ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no \
                        ${REMOTE_USER}@${REMOTE_HOST} "mkdir -p ${REMOTE_TAR_DIR} ${REMOTE_BASE_DIR}"

                    # Remove any old/stale yaml so a rename or removed file never
                    # lingers on the remote host and gets silently re-applied later
                    ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no \
                        ${REMOTE_USER}@${REMOTE_HOST} "rm -f ${REMOTE_BASE_DIR}/*.yaml"

                    # Copy TAR file
                    scp -i ${SSH_KEY} -o StrictHostKeyChecking=no \
                        ${TAR_DIR}/${TAR_FILE} \
                        ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_TAR_DIR}/

                    # Copy Kubernetes YAML files (from repo) to BASE_DIR
                    scp -i ${SSH_KEY} -o StrictHostKeyChecking=no \
                        ${WORKDIR}/k8s/*.yaml \
                        ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE_DIR}/
                """
            }
        }

        stage('Deploy Oras Skopeo on Remote Server') {
            steps {
                sh """
                echo "➡️ Deploying oras-skopeo-api on remote server..."
                ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} \
                    "bash ${SCRIPT_DIR}/${DEPLOY_SCRIPT}"
                """
            }
        }

    }

    post {
        success {
            echo '✅ Oras-Skopeo API Build → TAR → Copy → Deploy Successful!'
        }
        failure {
            echo '❌ Oras-Skopeo API Pipeline Failed!'
        }
    }
}
