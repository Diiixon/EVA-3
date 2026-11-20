import os
import secrets
import sqlite3
import time

from flask import Flask, request, render_template_string, redirect, session
from flask_wtf.csrf import CSRFProtect
from prometheus_flask_exporter import PrometheusMetrics
from werkzeug.security import check_password_hash

app = Flask(__name__)
PrometheusMetrics(app)  # expone /metrics para Prometheus/Grafana (peticiones por código HTTP, CPU, RAM)
# Clave desde variable de entorno; si falta, una aleatoria (nunca hardcodeada en el código)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    # Secure solo viaja por HTTPS; activar con COOKIE_SECURE=1 cuando haya TLS
    SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE') == '1',
)
csrf = CSRFProtect(app)

MAX_INTENTOS, BLOQUEO_SEG = 5, 300
# shortcut: contador en memoria, se pierde al reiniciar y no se comparte entre procesos; usar Flask-Limiter/Redis si se escala
intentos_fallidos = {}


@app.after_request
def cabeceras_seguridad(resp):
    """Cabeceras HTTP de seguridad (alertas Medium/Low de OWASP ZAP)."""
    resp.headers.update({
        'Content-Security-Policy': "default-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'",
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
        'Cross-Origin-Opener-Policy': 'same-origin',
        'Cross-Origin-Resource-Policy': 'same-origin',
        'Cross-Origin-Embedder-Policy': 'require-corp',
    })
    return resp


def db_query(query, params=()):
    """Ejecuta queries parametrizadas: los datos nunca se concatenan al SQL."""
    conn = sqlite3.connect('vulnerable.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchall()
    conn.commit()
    conn.close()
    return result


# --- LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username', '')
        pw = request.form.get('password', '')

        fallos, desde = intentos_fallidos.get(user, (0, 0))
        if fallos >= MAX_INTENTOS and time.time() - desde < BLOQUEO_SEG:
            return "<h3>Cuenta bloqueada temporalmente</h3><a href='/login'>Volver</a>", 429

        usuarios = db_query("SELECT * FROM usuarios WHERE username = ?", (user,))
        if usuarios and check_password_hash(usuarios[0]['password'], pw):
            intentos_fallidos.pop(user, None)
            session.clear()
            session['username'] = usuarios[0]['username']
            return redirect('/dashboard')

        intentos_fallidos[user] = (fallos + 1, time.time())
        return "<h3>Acceso denegado</h3><a href='/login'>Volver</a>", 401

    return render_template_string('''
        <h2>Login del Sistema Académico</h2>
        <form method="post">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            Usuario: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Ingresar">
        </form>
    ''')


# --- DASHBOARD ---
@app.route('/dashboard')
def dashboard():
    username = session.get('username')
    if not username:
        return redirect('/login')

    filas = db_query("SELECT * FROM usuarios WHERE username = ?", (username,))
    if not filas:
        session.clear()
        return redirect('/login')

    # Variables de plantilla Jinja: se escapan automáticamente (sin f-strings)
    return render_template_string('''
    <h1>Panel de {{ datos['username'] }}</h1>
    <p><b>Rol:</b> {{ datos['rol'] }}</p>
    <p><b>Biografía:</b> {{ datos['bio'] }}</p>
    <hr>
    <h3>Actualizar Biografía</h3>
    <form action="/update_bio" method="POST">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <input type="text" name="nueva_bio" placeholder="Escribe algo...">
        <input type="submit" value="Guardar Cambios">
    </form>
    <br><a href="/logout">Cerrar Sesión</a>
    ''', datos=filas[0])


@app.route('/update_bio', methods=['POST'])
def update_bio():
    username = session.get('username')
    if username:
        nueva_bio = request.form.get('nueva_bio', '')
        db_query("UPDATE usuarios SET bio = ? WHERE username = ?", (nueva_bio, username))
    return redirect('/dashboard')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/')
def home():
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=False, port=5000)
