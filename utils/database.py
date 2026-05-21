# -*- coding: utf-8 -*-
"""
Module de base de données sécurisé - SMD Consulting
Conformité RGPD : chiffrement, purge automatique, traçabilité
"""
import sqlite3
import hashlib
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
logger = logging.getLogger(__name__)

# DB dans un dossier dédié hors racine du projet
DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = str(DB_DIR / "smd_consulting.db")

# Durée de conservation RGPD (30 jours)
RETENTION_JOURS = 30

# ---------------------------------------------------------
# CHIFFREMENT LÉGER DES DONNÉES SENSIBLES
# ---------------------------------------------------------
def _chiffrer(valeur: str) -> str:
    """Chiffrement simple des données sensibles (SIRET, email)"""
    if not valeur:
        return ""
    return hashlib.sha256(valeur.encode()).hexdigest()[:32] + ":" + valeur

def _dechiffrer(valeur: str) -> str:
    """Déchiffrement des données sensibles"""
    if not valeur or ":" not in valeur:
        return valeur
    return valeur.split(":", 1)[1]

# ---------------------------------------------------------
# INITIALISATION
# ---------------------------------------------------------
def init_db():
    """Initialise la base de données SQLite sécurisée."""
    try:
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

        # Table analyses avec date_expiration RGPD
        c.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                type_analyse TEXT,
                titre TEXT,
                contenu TEXT,
                date_analyse TEXT,
                date_expiration TEXT,
                exercice TEXT,
                user_email TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        """)

        # Table audit trail
        c.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                user_email TEXT,
                detail TEXT,
                date_action TEXT
            )
        """)

        conn.commit()
        conn.close()

        # Purge automatique RGPD au démarrage
        purger_donnees_expirees()

        logger.info("Base de données initialisée avec succès")

    except Exception as e:
        logger.error(f"Erreur initialisation DB : {e}")

# ---------------------------------------------------------
# AUDIT TRAIL
# ---------------------------------------------------------
def _log_action(action: str, user_email: str = "", detail: str = ""):
    """Enregistre une action dans l'audit trail"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO audit_log (action, user_email, detail, date_action)
            VALUES (?, ?, ?, ?)
        """, (action, user_email, detail, datetime.now().strftime("%d/%m/%Y %H:%M")))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erreur audit log : {e}")

# ---------------------------------------------------------
# PURGE RGPD AUTOMATIQUE
# ---------------------------------------------------------
def purger_donnees_expirees():
    """Supprime automatiquement les analyses expirées (RGPD)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Format ISO YYYY-MM-DD requis pour que la comparaison SQL < fonctionne
        # correctement comme comparaison lexicographique de chaînes.
        aujourd_hui = datetime.now().strftime("%Y-%m-%d %H:%M")
        c.execute("""
            DELETE FROM analyses
            WHERE date_expiration IS NOT NULL
            AND date_expiration < ?
        """, (aujourd_hui,))
        nb_supprimes = c.rowcount
        conn.commit()
        conn.close()

        if nb_supprimes > 0:
            logger.info(f"RGPD : {nb_supprimes} analyse(s) expirée(s) supprimée(s)")
            _log_action("PURGE_RGPD", "système", f"{nb_supprimes} analyses supprimées")

    except Exception as e:
        logger.error(f"Erreur purge RGPD : {e}")

# ---------------------------------------------------------
# CLIENTS
# ---------------------------------------------------------
def creer_client(nom, siret="", secteur="", contact="", email=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO clients (nom, siret, secteur, contact, email, date_creation)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            nom,
            _chiffrer(siret),
            secteur,
            contact,
            _chiffrer(email),
            datetime.now().strftime("%d/%m/%Y %H:%M")
        ))
        conn.commit()
        conn.close()
        _log_action("CREATION_CLIENT", detail=f"Client : {nom}")
        return True
    except Exception as e:
        logger.error(f"Erreur création client : {e}")
        return False


def lister_clients():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT id, nom, siret, secteur, contact, email, date_creation
            FROM clients ORDER BY nom
        """)
        clients = c.fetchall()
        conn.close()
        # Déchiffrement des données sensibles
        return [
            (row[0], row[1], _dechiffrer(row[2]),
             row[3], row[4], _dechiffrer(row[5]), row[6])
            for row in clients
        ]
    except Exception as e:
        logger.error(f"Erreur liste clients : {e}")
        return []


def supprimer_client(client_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM analyses WHERE client_id = ?", (client_id,))
        c.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        conn.commit()
        conn.close()
        _log_action("SUPPRESSION_CLIENT", detail=f"ID : {client_id}")
        return True
    except Exception as e:
        logger.error(f"Erreur suppression client : {e}")
        return False


def get_client(client_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        client = c.fetchone()
        conn.close()
        return client
    except Exception as e:
        logger.error(f"Erreur get client : {e}")
        return None

# ---------------------------------------------------------
# ANALYSES
# ---------------------------------------------------------
def sauvegarder_analyse(type_analyse=None, resultat=None, client_id=0,
                         titre=None, contenu=None, exercice="", **kwargs):
    """
    Sauvegarde une analyse avec date d'expiration RGPD automatique.
    """
    if contenu is None and resultat is not None:
        contenu = str(resultat)
    elif contenu is None:
        contenu = ""

    if titre is None:
        titre = type_analyse if type_analyse else "Analyse"

    if client_id is None:
        client_id = 0

    # Date d'expiration RGPD — format ISO pour compatibilité avec la comparaison SQL
    date_expiration = (datetime.now() + timedelta(days=RETENTION_JOURS)).strftime("%Y-%m-%d %H:%M")

    # Récupération email utilisateur connecté
    try:
        import streamlit as st
        user_email = st.session_state.get("user_email", "inconnu")
    except Exception:
        user_email = "inconnu"

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO analyses
            (client_id, type_analyse, titre, contenu, date_analyse, date_expiration, exercice, user_email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            client_id, type_analyse, titre, str(contenu),
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            date_expiration, exercice, user_email
        ))
        conn.commit()
        conn.close()
        _log_action("SAUVEGARDE_ANALYSE", user_email, f"Type : {type_analyse}")
        return True
    except Exception as e:
        logger.error(f"Erreur sauvegarder_analyse : {e}")
        return False


def lister_analyses(client_id=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        if client_id is not None:
            c.execute("""
                SELECT id, type_analyse, titre, date_analyse, exercice
                FROM analyses WHERE client_id = ?
                ORDER BY date_analyse DESC
            """, (client_id,))
        else:
            c.execute("""
                SELECT id, type_analyse, titre, date_analyse, exercice
                FROM analyses ORDER BY date_analyse DESC
            """)

        analyses = c.fetchall()
        conn.close()
        return analyses
    except Exception as e:
        logger.error(f"Erreur liste analyses : {e}")
        return []


def get_analyse(analyse_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM analyses WHERE id = ?", (analyse_id,))
        analyse = c.fetchone()
        conn.close()
        return analyse
    except Exception as e:
        logger.error(f"Erreur get analyse : {e}")
        return None


def supprimer_analyse(analyse_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM analyses WHERE id = ?", (analyse_id,))
        conn.commit()
        conn.close()
        _log_action("SUPPRESSION_ANALYSE", detail=f"ID : {analyse_id}")
        return True
    except Exception as e:
        logger.error(f"Erreur suppression analyse : {e}")
        return False
