import sqlite3
from pathlib import Path
from .security import hash_password, verify_password

DB_PATH = Path("users.db")

def init_user_db():
    """
    Initialise la base utilisateurs si elle n'existe pas.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
    """)
    conn.commit()
    conn.close()

def create_user(email: str, password: str, role: str = "user") -> bool:
    """
    Crée un utilisateur avec un mot de passe hashé.
    Retourne False si l'email existe déjà.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)",
            (email.lower(), hash_password(password), role),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(email: str, password: str):
    """
    Vérifie les identifiants et retourne un dict utilisateur si OK.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, email, password_hash, role FROM users WHERE email = ?",
        (email.lower(),)
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    user_id, email, pwd_hash, role = row

    if verify_password(password, pwd_hash):
        return {"id": user_id, "email": email, "role": role}

    return None

