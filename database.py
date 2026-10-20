import sqlite3
import os


DB_PATH = os.path.join(os.path.dirname(__file__), "flash_sale.db")

def get_db_connection():
    """Ouvre une connexion SQLite optimisée pour les requêtes simultanées."""
    conn = sqlite3.connect(DB_PATH, timeout=20.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Permet d'accéder aux données par nom de colonne: row["name"]
    
    
    conn.execute("PRAGMA journal_mode = WAL;")
    
    
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Crée les tables et ajoute des produits de test."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
       
       
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL CHECK (stock >= 0)
            );
        """)
        
        
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                idempotency_key TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id)
            );
        """)
        
        
        cursor.execute("SELECT COUNT(*) AS count FROM products")
        if cursor.fetchone()["count"] == 0:
            cursor.executemany("""
                INSERT INTO products (name, price, stock) VALUES (?, ?, ?)
            """, [
                ("PlayStation 5 (Vente Flash)", 399.99, 5),   # Seulement 5 unités !
                ("Casque Sony WH-1000XM5", 199.99, 10),       # 10 unités
                ("iPhone 15 Pro", 899.99, 3)                  # 3 unités
            ])
            conn.commit()
            print("Base de données initialisée avec des produits de test !")

if __name__ == "__main__":
    init_db()