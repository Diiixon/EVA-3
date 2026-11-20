
pipeline {
    agent any

    environment {
        IMAGE_NAME = 'eva3-laweb'
        CONTAINER_NAME = 'eva3-laweb'
        APP_PORT = '5000'
    }

    stages {
        stage('Build') {
            steps {
                echo 'Construyendo imagen Docker...'
                sh 'docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} .'
            }
        }

        stage('Test') {
            steps {
                echo 'Verificando que la imagen Docker se haya creado...'
                sh 'docker image inspect ${IMAGE_NAME}:${BUILD_NUMBER}'
            }
        }

        stage('Deploy') {
            steps {
                echo 'Desplegando aplicación...'
                sh '''
                    docker stop ${CONTAINER_NAME} || true
                    docker rm ${CONTAINER_NAME} || true
                    docker run -d \
                      --name ${CONTAINER_NAME} \
                      --restart unless-stopped \
                      -p ${APP_PORT}:5000 \
                      ${IMAGE_NAME}:${BUILD_NUMBER}
                '''
            }
        }
    }

    post {
        success {
            echo 'Pipeline completado correctamente.'
        }
        failure {
            echo 'El pipeline ha fallado. Revisar los registros.'
        }
    }
}
