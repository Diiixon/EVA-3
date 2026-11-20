
pipeline {
    agent any

    environment {
        IMAGE_NAME = 'eva3-laweb'
        CONTAINER_NAME = 'eva3-laweb'
        APP_PORT = '5000'
        TEST_PORT = '5001'
    }

    stages {

        stage('Build') {
            steps {
                echo 'Construyendo imagen Docker...'

                sh '''
                    docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} .
                '''
            }
        }

        stage('Test - OWASP ZAP') {
            steps {
                echo 'Verificando imagen Docker...'

                sh '''
                    docker image inspect ${IMAGE_NAME}:${BUILD_NUMBER}
                '''

                echo 'Preparando aplicación vulnerable para ZAP...'

                sh '''
                    set -eu

                    TEST_CONTAINER="eva3-laweb-zap-test-${BUILD_NUMBER}"
                    ZAP_CONTAINER="zap-scan-${BUILD_NUMBER}"

                    cleanup() {
                        docker rm -f "$TEST_CONTAINER" >/dev/null 2>&1 || true
                        docker rm -f "$ZAP_CONTAINER" >/dev/null 2>&1 || true
                    }

                    trap cleanup EXIT

                    docker rm -f "$TEST_CONTAINER" >/dev/null 2>&1 || true
                    docker rm -f "$ZAP_CONTAINER" >/dev/null 2>&1 || true

                    docker run -d \
                        --name "$TEST_CONTAINER" \
                        -p ${TEST_PORT}:5000 \
                        ${IMAGE_NAME}:${BUILD_NUMBER}

                    echo "Esperando que la aplicación inicie..."

                    APP_READY=0

                    for i in $(seq 1 30); do
                        if docker exec "$TEST_CONTAINER" python -c \
                            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/login', timeout=2)" \
                            >/dev/null 2>&1; then
                            APP_READY=1
                            break
                        fi

                        sleep 2
                    done

                    if [ "$APP_READY" -ne 1 ]; then
                        echo "La aplicación no respondió dentro del tiempo esperado."
                        docker logs "$TEST_CONTAINER" || true
                        exit 1
                    fi

                    echo "Aplicación disponible para el análisis."

                    mkdir -p "$JENKINS_HOME/zap-reports/$BUILD_TAG"
                    mkdir -p "$WORKSPACE/zap-reports"

                    HOST_REPORT_DIR="/var/lib/docker/volumes/jenkins_home/_data/zap-reports/$BUILD_TAG"

                    echo "Iniciando OWASP ZAP..."

                    set +e

                    timeout --signal=TERM --kill-after=20s 10m \
                    docker run \
                        --name "$ZAP_CONTAINER" \
                        --rm \
                        --network host \
                        --memory=3g \
                        --memory-swap=3g \
                        --cpus=2 \
                        -e JAVA_TOOL_OPTIONS="-Xmx2048m" \
                        -v "$HOST_REPORT_DIR:/zap/wrk/:rw" \
                        ghcr.io/zaproxy/zaproxy:stable \
                        zap-full-scan.py \
                        -t http://localhost:5001:${TEST_PORT} \
                        -m 1 \
                        -T 3 \
                        -r zap-report.html \
                        -J zap-report.json \
                        -I \
                        -z "-config scanner.threadPerHost=1"

                    ZAP_STATUS=$?

                    set -e

                    echo "Código de salida de ZAP: $ZAP_STATUS"

                    cp -a "$JENKINS_HOME/zap-reports/$BUILD_TAG/." \
                        "$WORKSPACE/zap-reports/" || true

                    if [ "$ZAP_STATUS" -eq 124 ] || [ "$ZAP_STATUS" -eq 137 ]; then
                        echo "El escaneo superó el tiempo máximo o fue terminado por el sistema."
                        exit 1
                    fi

                    if [ "$ZAP_STATUS" -eq 3 ]; then
                        echo "Error durante la ejecución de OWASP ZAP."
                        exit 1
                    fi

                    echo "Análisis de seguridad finalizado."
                '''
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
        always {
            echo 'Publicando informes de OWASP ZAP...'

            archiveArtifacts artifacts: 'zap-reports/**',
                             allowEmptyArchive: true

            sh '''
                docker rm -f eva3-laweb-zap-test-${BUILD_NUMBER} \
                    >/dev/null 2>&1 || true

                docker rm -f zap-scan-${BUILD_NUMBER} \
                    >/dev/null 2>&1 || true
            '''
        }

        success {
            echo 'Pipeline completado correctamente.'
        }

        failure {
            echo 'El pipeline ha fallado. Revisar los registros.'
        }
    }
}
