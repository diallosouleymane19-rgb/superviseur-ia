import sqlite3
import os

DB_PATH = "historique_factures.db"


# ---------------------------------------------------------
# INITIALISATION DE LA BASE
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            adresse TEXT,
            siret TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historique (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contenu TEXT,
            analyse TEXT,
            montant REAL,
            compte TEXT
        )
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------
# CLIENTS
# ---------------------------------------------------------
def ajouter_client(nom, adresse, siret):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO clients (nom, adresse, siret) VALUES (?, ?, ?)", (nom, adresse, siret))
    conn.commit()
    conn.close()


def lister_clients():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT nom, adresse, siret FROM clients")
    rows = cursor.fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------
# HISTORIQUE FACTURES
# ---------------------------------------------------------
def sauvegarder_facture(contenu, analyse, montant, compte):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO historique (contenu, analyse, montant, compte) VALUES (?, ?, ?, ?)",
        (contenu, analyse, montant, compte)
    )
    conn.commit()
    conn.close()


def charger_historique():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT contenu, analyse, montant, compte FROM historique")
    rows = cursor.fetchall()
    conn.close()
    return rows


def vider_historique():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM historique")
    conn.commit()
    conn.close()

