import sqlite3

DB_NAME = 'inventario_completo.db'  # Cambia aquí si tu base de datos se llama diferente

def agregar_columna_precio():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(equipos)")
        columnas = [col[1] for col in cursor.fetchall()]
        if 'precio' not in columnas:
            cursor.execute('ALTER TABLE equipos ADD COLUMN precio REAL DEFAULT 0')
            print("Columna 'precio' agregada con éxito.")
        else:
            print("La columna 'precio' ya existe.")
        conn.commit()

if __name__ == "__main__":
    agregar_columna_precio()
