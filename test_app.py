"""Pruebas de regresión de seguridad. Ejecutar: python test_app.py (sale con error si alguna falla)."""
import os
import re
import sqlite3
import tempfile

os.chdir(tempfile.mkdtemp())  # BD temporal: no toca la real
os.environ['ADMIN_PASSWORD'] = 'Adm1n-Pruebas-Seguras!'
os.environ['ALUMNO_PASSWORD'] = 'Alumn0-Pruebas-Seguras!'

import init_db
import app as modulo

init_db.crear_base_de_datos()
app = modulo.app


def cliente_logueado(usuario, password):
    c = app.test_client()
    token = re.search(r'name="csrf_token" value="([^"]+)"', c.get('/login').text).group(1)
    r = c.post('/login', data={'username': usuario, 'password': password, 'csrf_token': token})
    return c, r


def token_dashboard(c):
    return re.search(r'name="csrf_token" value="([^"]+)"', c.get('/dashboard').text).group(1)


# 1. SQL Injection: el bypass clásico ya no autentica
_, r = cliente_logueado('admin', "' OR 1=1 --")
assert r.status_code == 401, 'SQLi permitió login'
_, r = cliente_logueado("admin' --", 'x')
assert r.status_code == 401, 'SQLi en usuario permitió login'

# Login legítimo funciona
c, r = cliente_logueado('admin', os.environ['ADMIN_PASSWORD'])
assert r.status_code == 302 and r.location.endswith('/dashboard'), 'login válido falló'

# 2. XSS almacenado: el payload se guarda pero se muestra escapado
c.post('/update_bio', data={'nueva_bio': '<script>alert(1)</script>', 'csrf_token': token_dashboard(c)})
html = c.get('/dashboard').text
assert '<script>alert(1)</script>' not in html and '&lt;script&gt;' in html, 'XSS no escapado'

# 3. CSRF: un POST sin token (página externa) es rechazado
r = c.post('/update_bio', data={'nueva_bio': 'ESTA CUENTA FUE HACKEADA'})
assert r.status_code == 400, 'POST sin token CSRF aceptado'
assert 'HACKEADA' not in c.get('/dashboard').text

# 4. Suplantación: una cookie user_session=alumno ya no da acceso
c2 = app.test_client()
c2.set_cookie('user_session', 'alumno')
assert c2.get('/dashboard').status_code == 302, 'cookie manipulada aceptada'
cookie = c.get_cookie('session')
assert cookie.http_only and cookie.same_site == 'Lax', 'flags de cookie faltantes'

# 5. Contraseñas hasheadas en la BD
pw = sqlite3.connect('vulnerable.db').execute("SELECT password FROM usuarios WHERE username='admin'").fetchone()[0]
assert pw != os.environ['ADMIN_PASSWORD'] and pw.startswith(('scrypt:', 'pbkdf2:')), 'contraseña en texto plano'

# 6. Credenciales débiles ya no sirven + bloqueo por intentos repetidos
_, r = cliente_logueado('alumno', '12345')
assert r.status_code == 401, 'credencial débil aceptada'
for _ in range(modulo.MAX_INTENTOS):
    cliente_logueado('alumno', 'mala')
_, r = cliente_logueado('alumno', os.environ['ALUMNO_PASSWORD'])
assert r.status_code == 429, 'sin bloqueo tras intentos fallidos'

# 7. Debug deshabilitado
assert not app.debug, 'debug activo'

# Cabeceras de seguridad (hallazgos de OWASP ZAP)
h = app.test_client().get('/login').headers
for cab in ('Content-Security-Policy', 'X-Frame-Options', 'X-Content-Type-Options'):
    assert cab in h, f'falta cabecera {cab}'

print('OK: 7 controles de seguridad + cabeceras verificados')
