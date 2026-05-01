import sqlite3
import json
from datetime import datetime
import os

DB_PATH = "smd_consulting.db"

def init_db():
    """
    Initialise la base de données SQLite.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Table clients
    c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            siret TEXT,
            secteur TEXT,
            contact TEXT,
            email TEXT,
            date_creation TEXT
        )
    """)

    # Table analyses
    c.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            type_analyse TEXT,
            titre TEXT,
            contenu TEXT,
            date_analyse TEXT,
            exercice TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)

    conn.commit()
    conn.close()

# ---------------------------------------------------------
# CLIENTS
# ---------------------------------------------------------
def creer_client(nom, siret="", secteur="", contact="", email=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO clients (nom, siret, secteur, contact, email, date_creation)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (nom, siret, secteur, contact, email, datetime.now().strftime("%d/%m/%Y %H:%M")))
    conn.commit()
    conn.close()

def lister_clients():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, nom, siret, secteur, contact, email, date_creation FROM clients ORDER BY nom")
    clients = c.fetchall()
    conn.close()
    return clients

def supprimer_client(client_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM analyses WHERE client_id = ?", (client_id,))
    c.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# ANALYSES
# ---------------------------------------------------------
def sauvegarder_analyse(client_id, type_analyse, titre, contenu, exercice=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO analyses (client_id, type_analyse, titre, contenu, date_analyse, exercice)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (client_id, type_analyse, titre, contenu, datetime.now().strftime("%d/%m/%Y %H:%M"), exercice))
    conn.commit()
    conn.close()

def lister_analyses(client_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, type_analyse, titre, date_analyse, exercice
        FROM analyses
        WHERE client_id = ?
        ORDER BY date_analyse DESC
    """, (client_id,))
    analyses = c.fetchall()
    conn.close()
    return analyses

def get_analyse(analyse_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM analyses WHERE id = ?", (analyse_id,))
    analyse = c.fetchone()
    conn.close()
    return analyse

def supprimer_analyse(analyse_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM analyses WHERE id = ?", (analyse_id,))
    conn.commit()
    conn.close()

def get_client(client_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
    client = c.fetchone()
    conn.close()
    return client