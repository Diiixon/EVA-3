import os
import secrets
import sqlite3

from werkzeug.security import generate_password_hash


def crear_base_de_datos():
    conexion = sqlite3.connect('vulnerable.db')
    cursor = conexion.cursor()

    cursor.execute('DROP TABLE IF EXISTS usuarios')
    cursor.execute('''
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            rol TEXT NOT NULL,
            bio TEXT
        )
    ''')

    # Contraseñas desde variables de entorno; si faltan se generan aleatorias y fuertes
    admin_pw = os.environ.get('ADMIN_PASSWORD') or secrets.token_urlsafe(16)
    alumno_pw = os.environ.get('ALUMNO_PASSWORD') or secrets.token_urlsafe(16)

    usuarios = [
        ('admin', generate_password_hash(admin_pw), 'admin', 'Cuenta de administrador del sistema.'),
        ('alumno', generate_password_hash(alumno_pw), 'user', 'Soy un estudiante aprendiendo hacking.')
    ]

    cursor.executemany('INSERT INTO usuarios (username, password, rol, bio) VALUES (?, ?, ?, ?)', usuarios)
    conexion.commit()
    conexion.close()
    print("Base de datos inicializada con contraseñas hasheadas.")
    if 'ADMIN_PASSWORD' not in os.environ:
        print(f"Contraseña generada admin: {admin_pw}")
    if 'ALUMNO_PASSWORD' not in os.environ:
        print(f"Contraseña generada alumno: {alumno_pw}")


if __name__ == "__main__":
    crear_base_de_datos()
