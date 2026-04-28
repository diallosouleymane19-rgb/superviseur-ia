import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("historique_factures.db")

def init_db():
    """
    Initialise les tables clients + factures si elles n'existent pas.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            nom TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS factures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            client_id INTEGER,
            date_analyse TEXT,
            num_facture TEXT,
            fournisseur TEXT,
            montant_ht REAL,
            tva REAL,
            montant_ttc REAL,
            compte_suggere TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

# ---------------- CLIENTS ---------------- #

def ajouter_client(user_id: int, nom: str):
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO clients (user_id, nom) VALUES (?, ?)",
            (user_id, nom.strip()),
        )

def lister_clients(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, nom FROM clients WHERE user_id = ? ORDER BY nom",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

# ---------------- FACTURES ---------------- #

def sauvegarder_facture(user_id: int, client_id: int | None, infos: dict, compte: str):
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO factures (
                user_id, client_id, date_analyse, num_facture, fournisseur,
                montant_ht, tva, montant_ttc, compte_suggere
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            client_id,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            str(infos.get("num_facture", "")),
            str(infos.get("fournisseur", "")),
            float(infos.get("montant_ht", 0.0)),
            float(infos.get("tva", 0.0)),
            float(infos.get("montant_ttc", 0.0)),
            compte,
        ))

def charger_historique(user_id: int, limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT f.id, f.date_analyse, c.nom, f.num_facture, f.fournisseur,
               f.montant_ht, f.tva, f.montant_ttc, f.compte_suggere
        FROM factures f
        LEFT JOIN clients c ON f.client_id = c.id
        WHERE f.user_id = ?
        ORDER BY f.id DESC
        LIMIT ?
    """, (user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows

def vider_historique(user_id: int):
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM factures WHERE user_id = ?", (user_id,))

