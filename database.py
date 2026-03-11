import sqlite3
import mysql.connector
import os

class DatabaseManager:
    def __init__(self, db_name="dx_bot.db"):
        self.db_path = os.path.join("/app", "data", db_name)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.db_path):
            open(self.db_path, "a", encoding="utf-8").close()
        self.conn = sqlite3.connect(self.db_path)
        # Agregamos la columna rbn_enabled (1=ON, 0=OFF)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS filtros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                indicativo TEXT,
                bandas TEXT,
                modos TEXT, 
                lang TEXT,
                rbn_enabled INTEGER DEFAULT 1
            )""")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
        self.conn.commit()

    def register_user_if_new(self, u_id):
        """Registers user if missing and returns True only on first registration."""
        c = self.conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
        self.conn.commit()
        return c.rowcount > 0

    def add_filter(self, u_id, call, bands, modes, lang):
        bands_norm = bands.strip().lower()
        modes_norm = modes.strip().upper()

        # Accept common wildcards for "all bands" and "all modes".
        if bands_norm in ("all", "*", "todas"):
            bands_norm = "all"
        if modes_norm in ("ALL", "*", "TODOS"):
            modes_norm = "ALL"

        # Corregido: 6 columnas y 6 valores (5 dinámicos + 1 fijo)
        self.conn.execute(
            "INSERT INTO filtros (user_id, indicativo, bandas, modos, lang, rbn_enabled) VALUES (?,?,?,?,?,1)",
            (u_id, call.upper(), bands_norm, modes_norm, lang)
        )
        self.conn.commit()

    def get_user_filters(self, u_id):
        # Seleccionamos las columnas explícitamente para evitar líos
        cursor = self.conn.execute(
            "SELECT id, indicativo, bandas, modos, rbn_enabled FROM filtros WHERE user_id = ?", 
            (u_id,)
        )
        return cursor.fetchall()

    def delete_filter(self, u_id, f_id):
        c = self.conn.execute("DELETE FROM filtros WHERE id = ? AND user_id = ?", (f_id, u_id))
        self.conn.commit()
        return c.rowcount > 0

    def update_rbn_preference(self, u_id, status):
        val = 1 if status == "on" else 0
        self.conn.execute("UPDATE filtros SET rbn_enabled = ? WHERE user_id = ?", (val, u_id))
        self.conn.commit()

    def find_interested_users(self, dx_call, banda, modo, is_rbn):
        cursor = self.conn.cursor()
        rbn_clause = "AND rbn_enabled = 1" if is_rbn else ""
        query = f"""
            SELECT DISTINCT user_id, lang FROM filtros 
            WHERE (indicativo = ? OR indicativo = 'ALL') 
            AND (LOWER(bandas) LIKE ? OR LOWER(bandas) = 'all') 
            AND (UPPER(modos) LIKE ? OR UPPER(modos) = 'ALL')
            {rbn_clause}
        """
        cursor.execute(query, (dx_call.upper(), f"%{banda.lower()}%", f"%{modo.upper()}%"))
        return cursor.fetchall()

    def get_recent_spots(self, indicativo, minutos=30):
        try:
            db_spider = mysql.connector.connect(
                host=os.getenv("CLUSTER_DB_HOST", "dxspider-db"),
                user=os.getenv("CLUSTER_DB_USER"),
                password=os.getenv("CLUSTER_DB_PASS"),
                database=os.getenv("CLUSTER_DB_NAME")
            )
            cursor = db_spider.cursor(dictionary=True)
            query = """
                SELECT freq, dxcall, comment, time 
                FROM spots 
                WHERE (dxcall = %s OR %s = 'ALL')
                AND (time >= UNIX_TIMESTAMP(NOW() - INTERVAL %s MINUTE))
                ORDER BY time DESC LIMIT 10
            """
            cursor.execute(query, (indicativo, indicativo, minutos))
            results = cursor.fetchall()
            db_spider.close()
            return results
        except:
            return []

    def get_user_filters(self, u_id):
        return self.conn.execute("SELECT id, indicativo, bandas, modos FROM filtros WHERE user_id = ?", (u_id,)).fetchall()

    def delete_filter(self, u_id, f_id):
        c = self.conn.execute("DELETE FROM filtros WHERE id = ? AND user_id = ?", (f_id, u_id))
        self.conn.commit()
        return c.rowcount > 0