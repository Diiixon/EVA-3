pipeline {
    agent any

    environment {
        IMAGE_NAME     = 'eva3-laweb'
        CONTAINER_NAME = 'eva3-app'
        NETWORK        = 'eva3-net'
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
                echo 'Pruebas de seguridad del código (7 ataques) y auditoría de dependencias...'
                sh 'docker run --rm ${IMAGE_NAME}:${BUILD_NUMBER} python test_app.py'
                // pip-audit falla (exit 1) si alguna dependencia tiene un CVE conocido: detiene el pipeline
                sh 'docker run --rm ${IMAGE_NAME}:${BUILD_NUMBER} sh -c "pip install -q --user pip-audit && python -m pip_audit -r requirements.txt"'
            }
        }

        stage('Deploy') {
            steps {
                echo 'Desplegando aplicación...'
                sh '''
                    docker network create ${NETWORK} || true
                    docker stop ${CONTAINER_NAME} || true
                    docker rm ${CONTAINER_NAME} || true
                    docker run -d --name ${CONTAINER_NAME} --network ${NETWORK} -p 5000:5000 ${IMAGE_NAME}:${BUILD_NUMBER}
                    sleep 5
                '''
            }
        }

        stage('Security Scan (OWASP ZAP)') {
            steps {
                echo 'Escaneo dinámico con OWASP ZAP (spider + active scan)...'
                script {
                    sh 'docker rm -f zap || true; docker volume rm -f zapwrk || true'
                    // ZAP exige /zap/wrk montado; un volumen sirve también si Jenkins corre dentro de Docker
                    // 0 = sin alertas, 1 = FAIL, 2 = solo WARN, 3 = error de ZAP
                    def rc = sh(returnStatus: true, script: '''
                        docker run --name zap --network ${NETWORK} -u root -v zapwrk:/zap/wrk -t ghcr.io/zaproxy/zaproxy:stable \
                            zap-full-scan.py -t http://${CONTAINER_NAME}:5000 -m 2 \
                            -r zap-report.html -J zap-report.json
                    ''')
                    sh 'docker cp zap:/zap/wrk/zap-report.html . && docker cp zap:/zap/wrk/zap-report.json . && docker rm zap && docker volume rm zapwrk'
                    if (rc == 1 || rc == 3) { unstable("OWASP ZAP reportó alertas FAIL o un error (código ${rc})") }
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'zap-report.*', allowEmptyArchive: true
        }
    }
}
