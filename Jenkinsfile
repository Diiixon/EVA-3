
pipeline {
    agent any

    environment {
        APP_IMAGE = "eva3-laweb:${BUILD_NUMBER}"
        APP_CONTAINER = "eva3-laweb"
        TEST_CONTAINER = "eva3-laweb-zap-test-${BUILD_NUMBER}"
        ZAP_CONTAINER = "zap-scan-${BUILD_NUMBER}"
        DOCKER_NETWORK = "zap-network-${BUILD_NUMBER}"

        REPORT_DIR = "zap-reports"
        JENKINS_REPORT_BASE = "/var/jenkins_home/zap-reports"
        HOST_REPORT_BASE = "/var/lib/docker/volumes/jenkins_home/_data/zap-reports"
    }

    stages {

        stage('Build') {
            steps {
                echo 'Construyendo imagen Docker...'

                sh '''
                    docker build -t ${APP_IMAGE} .
                '''
            }
        }

        stage('Test - OWASP ZAP') {
            steps {
                echo 'Preparando aplicación para OWASP ZAP...'

                sh '''
                    set -eu

                    # Nombres y rutas de esta ejecución
                    REPORT_PATH="${JENKINS_REPORT_BASE}/jenkins-${JOB_NAME}-${BUILD_NUMBER}"
                    HOST_REPORT_PATH="${HOST_REPORT_BASE}/jenkins-${JOB_NAME}-${BUILD_NUMBER}"

                    cleanup() {
                        docker rm -f "${TEST_CONTAINER}" >/dev/null 2>&1 || true
                        docker rm -f "${ZAP_CONTAINER}" >/dev/null 2>&1 || true
                        docker network rm "${DOCKER_NETWORK}" >/dev/null 2>&1 || true
                    }

                    trap cleanup EXIT

                    # Limpiar posibles recursos anteriores
                    cleanup

                    # Preparar directorios de informes
                    mkdir -p "${REPORT_PATH}"
                    mkdir -p "${HOST_REPORT_PATH}"
                    mkdir -p "${WORKSPACE}/${REPORT_DIR}"

                    # Crear red Docker compartida
                    docker network create "${DOCKER_NETWORK}"

                    # Iniciar aplicación vulnerable dentro de la red
                    docker run -d \
                        --name "${TEST_CONTAINER}" \
                        --network "${DOCKER_NETWORK}" \
                        "${APP_IMAGE}"

                    echo "Esperando que la aplicación inicie..."

                    APP_READY=0

                    for i in $(seq 1 30); do
                        if docker exec "${TEST_CONTAINER}" python -c \
                            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/login', timeout=2)" \
                            >/dev/null 2>&1; then

                            APP_READY=1
                            break
                        fi

                        sleep 2
                    done

                    if [ "${APP_READY}" -ne 1 ]; then
                        echo "ERROR: La aplicación no inició correctamente."
                        docker logs "${TEST_CONTAINER}"
                        exit 1
                    fi

                    echo "Aplicación disponible para el análisis."

                    echo "Iniciando OWASP ZAP..."

                    set +e

                    timeout --signal=TERM --kill-after=20s 10m docker run \
                        --name "${ZAP_CONTAINER}" \
                        --network "${DOCKER_NETWORK}" \
                        --memory=3g \
                        --memory-swap=3g \
                        --cpus=2 \
                        -e JAVA_TOOL_OPTIONS="-Xmx2048m" \
                        -v "${HOST_REPORT_PATH}:/zap/wrk/:rw" \
                        ghcr.io/zaproxy/zaproxy:stable \
                        zap-full-scan.py \
                        -t "http://${TEST_CONTAINER}:5000" \
                        -m 1 \
                        -T 3 \
                        -r zap-report.html \
                        -J zap-report.json \
                        -I \
                        -z "-config scanner.threadPerHost=1"

                    ZAP_STATUS=$?

                    set -e

                    echo "Código de salida de ZAP: ${ZAP_STATUS}"

                    # Copiar informes al workspace de Jenkins
                    cp -a "${REPORT_PATH}/." "${WORKSPACE}/${REPORT_DIR}/" 2>/dev/null || true

                    # Comprobar resultado del análisis
                    if [ "${ZAP_STATUS}" -eq 124 ] || [ "${ZAP_STATUS}" -eq 137 ]; then
                        echo "ERROR: OWASP ZAP superó el tiempo máximo permitido."
                        exit 1
                    fi

                    if [ "${ZAP_STATUS}" -ne 0 ]; then
                        echo "ERROR: Falló la ejecución de OWASP ZAP."
                        exit 1
                    fi

                    # Verificar generación de informes
                    if [ ! -s "${WORKSPACE}/${REPORT_DIR}/zap-report.html" ]; then
                        echo "ERROR: No se generó el informe HTML."
                        exit 1
                    fi

                    if [ ! -s "${WORKSPACE}/${REPORT_DIR}/zap-report.json" ]; then
                        echo "ERROR: No se generó el informe JSON."
                        exit 1
                    fi

                    echo "Análisis OWASP ZAP completado correctamente."
                    echo "Informes HTML y JSON generados."
                '''
            }
        }

        stage('Deploy') {
            steps {
                echo 'Desplegando aplicación...'

                sh '''
                    docker rm -f "${APP_CONTAINER}" >/dev/null 2>&1 || true

                    docker run -d \
                        --name "${APP_CONTAINER}" \
                        -p 5000:5000 \
                        --restart unless-stopped \
                        "${APP_IMAGE}"

                    echo "Aplicación desplegada correctamente."
                '''
            }
        }
    }

    post {
        always {
            echo 'Publicando informes de OWASP ZAP...'

            archiveArtifacts(
                artifacts: 'zap-reports/**',
                allowEmptyArchive: true,
                fingerprint: true
            )

            sh '''
                docker rm -f "${TEST_CONTAINER}" >/dev/null 2>&1 || true
                docker rm -f "${ZAP_CONTAINER}" >/dev/null 2>&1 || true
                docker network rm "${DOCKER_NETWORK}" >/dev/null 2>&1 || true
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
