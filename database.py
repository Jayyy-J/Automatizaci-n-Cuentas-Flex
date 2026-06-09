import psycopg2
from psycopg2 import extras
from config import config
import json

def get_connection():
    return psycopg2.connect(config.DATABASE_URL)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Tabla de cuentas
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cuentas (
            id SERIAL PRIMARY KEY,
            correo TEXT UNIQUE NOT NULL,
            contrasena TEXT NOT NULL,
            foto_licencia_id TEXT,
            datos_pago TEXT,
            estado TEXT CHECK (estado IN ('en_proceso', 'completado', 'subir_datos_pago', 'lista_para_comercializar', 'vendida')),
            valor_venta NUMERIC DEFAULT 0
        );
    """)

    # Tabla para persistencia de estados del bot
    cur.execute("""
        CREATE TABLE IF NOT EXISTS estados_bot (
            user_id BIGINT PRIMARY KEY,
            state TEXT,
            data TEXT
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

def registrar_cuenta(correo, contrasena, foto_licencia_id, estado):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO cuentas (correo, contrasena, foto_licencia_id, estado)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (correo) DO UPDATE SET
                contrasena = EXCLUDED.contrasena,
                foto_licencia_id = EXCLUDED.foto_licencia_id,
                estado = EXCLUDED.estado;
        """, (correo, contrasena, foto_licencia_id, estado))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def actualizar_estado_cuenta(correo, nuevo_estado):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE cuentas SET estado = %s WHERE correo = %s", (nuevo_estado, correo))
    conn.commit()
    cur.close()
    conn.close()

def agregar_datos_pago(correo, datos_pago):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE cuentas SET datos_pago = %s WHERE correo = %s", (datos_pago, correo))
    conn.commit()
    cur.close()
    conn.close()

def registrar_valor_venta(correo, valor_venta):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE cuentas SET valor_venta = %s, estado = 'vendida' WHERE correo = %s", (valor_venta, correo))
    conn.commit()
    cur.close()
    conn.close()

def listar_cuentas_venta():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute("SELECT correo, contrasena FROM cuentas WHERE estado = 'lista_para_comercializar'")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_cuenta_por_correo_y_pass(correo, contrasena):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute("SELECT * FROM cuentas WHERE correo = %s AND contrasena = %s", (correo, contrasena))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row
