from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'inventario_patron'
DB_NAME = 'inventario_completo.db'

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                rol TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS equipos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                marca TEXT,
                modelo TEXT,
                estado TEXT,
                fecha_compra TEXT,
                fecha_mantenimiento TEXT,
                ubicacion TEXT,
                cantidad INTEGER,
                precio REAL,
                foto TEXT,
                observaciones TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipo_id INTEGER,
                cliente TEXT,
                cantidad INTEGER,
                fecha TEXT
            )
        ''')

        admin_exists = conn.execute('SELECT * FROM usuarios WHERE username = ?', ('admin',)).fetchone()
        if not admin_exists:
            conn.execute('INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)', ('admin', 'ruben123', 'admin'))
        conn.commit()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DB_NAME) as conn:
            user = conn.execute('SELECT * FROM usuarios WHERE username = ? AND password = ?', (username, password)).fetchone()
            if user:
                session['logged_in'] = True
                session['rol'] = user[3]
                if user[3] == 'admin':
                    return redirect(url_for('index'))
                else:
                    return redirect(url_for('ventas'))
    return render_template('login.html')

@app.route('/index')
def index():
    if not session.get('logged_in') or session.get('rol') != 'admin':
        return redirect(url_for('login'))
    with sqlite3.connect(DB_NAME) as conn:
        equipos = conn.execute('SELECT * FROM equipos').fetchall()
    return render_template('index.html', equipos=equipos, rol=session.get('rol'))

@app.route('/agregar_equipo', methods=['GET', 'POST'])
def agregar_equipo():
    if not session.get('logged_in') or session.get('rol') != 'admin':
        return "Acceso denegado", 403
    if request.method == 'POST':
        nombre = request.form['nombre']
        marca = request.form['marca']
        modelo = request.form['modelo']
        estado = request.form['estado']
        fecha_compra = request.form['fecha_compra']
        fecha_mantenimiento = request.form['fecha_mantenimiento']
        ubicacion = request.form['ubicacion']
        cantidad = int(request.form['cantidad'])
        precio = float(request.form['precio'])
        foto = request.form['foto']
        observaciones = request.form['observaciones']
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute('''
                INSERT INTO equipos (nombre, marca, modelo, estado, fecha_compra, fecha_mantenimiento, ubicacion, cantidad, precio, foto, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, marca, modelo, estado, fecha_compra, fecha_mantenimiento, ubicacion, cantidad, precio, foto, observaciones))
            conn.commit()
        return redirect(url_for('index'))
    return render_template('agregar_equipo.html')

@app.route('/editar_equipo/<int:id>', methods=['GET', 'POST'])
def editar_equipo(id):
    if not session.get('logged_in') or session.get('rol') != 'admin':
        return "Acceso denegado", 403
    with sqlite3.connect(DB_NAME) as conn:
        if request.method == 'POST':
            nombre = request.form['nombre']
            marca = request.form['marca']
            modelo = request.form['modelo']
            estado = request.form['estado']
            fecha_compra = request.form['fecha_compra']
            fecha_mantenimiento = request.form['fecha_mantenimiento']
            ubicacion = request.form['ubicacion']
            cantidad = int(request.form['cantidad'])
            precio = float(request.form['precio'])
            foto = request.form['foto']
            observaciones = request.form['observaciones']
            conn.execute('''
                UPDATE equipos SET nombre=?, marca=?, modelo=?, estado=?, fecha_compra=?, fecha_mantenimiento=?, ubicacion=?, cantidad=?, precio=?, foto=?, observaciones=?
                WHERE id=?
            ''', (nombre, marca, modelo, estado, fecha_compra, fecha_mantenimiento, ubicacion, cantidad, precio, foto, observaciones, id))
            conn.commit()
            return redirect(url_for('index'))
        equipo = conn.execute('SELECT * FROM equipos WHERE id = ?', (id,)).fetchone()
    return render_template('editar_equipo.html', equipo=equipo)

@app.route('/eliminar_equipo/<int:id>')
def eliminar_equipo(id):
    if not session.get('logged_in') or session.get('rol') != 'admin':
        return "Acceso denegado", 403
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('DELETE FROM equipos WHERE id = ?', (id,))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/ventas', methods=['GET', 'POST'])
def ventas():
    if not session.get('logged_in') or session.get('rol') not in ['admin', 'vendedor']:
        return redirect(url_for('login'))
    with sqlite3.connect(DB_NAME) as conn:
        equipos = conn.execute('SELECT * FROM equipos WHERE cantidad > 0').fetchall()
    if request.method == 'POST':
        equipo_id = int(request.form['equipo_id'])
        cliente = request.form['cliente']
        cantidad_vendida = int(request.form['cantidad'])
        with sqlite3.connect(DB_NAME) as conn:
            equipo = conn.execute('SELECT cantidad, precio FROM equipos WHERE id = ?', (equipo_id,)).fetchone()
            if equipo and equipo[0] >= cantidad_vendida:
                nueva_cantidad = equipo[0] - cantidad_vendida
                conn.execute('UPDATE equipos SET cantidad = ? WHERE id = ?', (nueva_cantidad, equipo_id))
                conn.execute('INSERT INTO ventas (equipo_id, cliente, cantidad, fecha) VALUES (?, ?, ?, ?)',
                             (equipo_id, cliente, cantidad_vendida, datetime.now().strftime('%Y-%m-%d')))
                conn.commit()
                venta_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
                return redirect(url_for('boleta', venta_id=venta_id))
            else:
                return "Stock insuficiente"
    return render_template('ventas.html', equipos=equipos)

@app.route('/boleta/<int:venta_id>')
def boleta(venta_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    with sqlite3.connect(DB_NAME) as conn:
        venta = conn.execute('''
            SELECT v.id, v.cliente, v.cantidad, v.fecha, e.nombre, e.precio
            FROM ventas v
            JOIN equipos e ON v.equipo_id = e.id
            WHERE v.id = ?
        ''', (venta_id,)).fetchone()
    if venta is None:
        return "Venta no encontrada"
    total = venta[2] * venta[5]  # cantidad * precio unitario
    return render_template('boleta.html', venta=venta, total=total)

@app.route('/historial_ventas')
def historial_ventas():
    if not session.get('logged_in') or session.get('rol') != 'admin':
        return redirect(url_for('login'))
    with sqlite3.connect(DB_NAME) as conn:
        ventas = conn.execute('''
            SELECT v.id, v.cliente, v.cantidad, v.fecha, e.nombre, e.precio
            FROM ventas v
            JOIN equipos e ON v.equipo_id = e.id
            ORDER BY v.fecha DESC
        ''').fetchall()
    return render_template('historial_ventas.html', ventas=ventas)

@app.route('/debug_equipos')
def debug_equipos():
    with sqlite3.connect(DB_NAME) as conn:
        equipos = conn.execute('SELECT * FROM equipos').fetchall()
    return {'equipos': equipos}

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
