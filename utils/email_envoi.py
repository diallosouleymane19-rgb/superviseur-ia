# -*- coding: utf-8 -*-
"""
utils/email_envoi.py - SMD Global Consulting LLC
Envoi d'e-mails par SMTP (boîte e-mail du domaine, par exemple chez OVH).

Secrets attendus dans secrets.toml (sur le serveur uniquement) :
    SMTP_HOST     = "ssl0.ovh.net"
    SMTP_PORT     = 465                      # 465 = SSL ; 587 = STARTTLS
    SMTP_USER     = "contact@smdconsulting.pro"
    SMTP_PASSWORD = "mot de passe de la boîte"
    SMTP_FROM     = "KontrolIA <contact@smdconsulting.pro>"   # facultatif
    SMTP_SECURITE = "ssl" | "starttls"       # facultatif, déduit du port
"""
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

import streamlit as st


def _secret(nom: str, defaut=""):
    try:
        v = st.secrets.get(nom)
        if v not in (None, ""):
            return v
    except Exception:
        pass
    return os.getenv(nom, defaut)


def email_configure() -> bool:
    """Vrai si l'envoi d'e-mails est paramétré (hôte, utilisateur et mot de passe présents)."""
    return all(_secret(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))


@st.cache_data(ttl=600, show_spinner=False)
def _serveur_joignable(hote: str, port: int) -> bool:
    """Test de connexion (5 s), gardé 10 minutes. Faux si l'hébergeur bloque la sortie vers le serveur d'envoi."""
    import socket
    try:
        socket.create_connection((hote, port), 5).close()
        return True
    except Exception as e:
        logging.error("Serveur d'envoi %s:%s injoignable (%s)", hote, port, type(e).__name__)
        return False


def envoi_possible() -> bool:
    """Paramétré ET serveur d'envoi joignable : sinon on propose l'adresse de contact au lieu d'un faux envoi."""
    if not email_configure():
        return False
    return _serveur_joignable(str(_secret("SMTP_HOST")), int(_secret("SMTP_PORT", 465)))


def envoyer_email(destinataire: str, sujet: str, texte: str) -> bool:
    """Envoie un e-mail en texte brut. Retourne True si le serveur l'a accepté."""
    if not email_configure():
        return False
    hote, port = _secret("SMTP_HOST"), int(_secret("SMTP_PORT", 465))
    utilisateur, mdp = _secret("SMTP_USER"), _secret("SMTP_PASSWORD")
    expediteur = _secret("SMTP_FROM") or formataddr(("KontrolIA", utilisateur))
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = expediteur, destinataire, sujet
    msg["Message-ID"] = make_msgid(domain=utilisateur.split("@")[-1])
    msg.set_content(texte)
    securite = str(_secret("SMTP_SECURITE", "ssl" if port == 465 else "starttls")).lower()
    try:
        contexte = ssl.create_default_context()
        if securite == "aucune":          # serveur de test local uniquement, jamais en production
            with smtplib.SMTP(hote, port, timeout=20) as s:
                s.send_message(msg)
        elif securite == "ssl":
            with smtplib.SMTP_SSL(hote, port, context=contexte, timeout=20) as s:
                s.login(utilisateur, mdp)
                s.send_message(msg)
        else:
            with smtplib.SMTP(hote, port, timeout=20) as s:
                s.starttls(context=contexte)
                s.login(utilisateur, mdp)
                s.send_message(msg)
        return True
    except Exception as e:      # le détail reste dans le journal du serveur, jamais à l'écran
        logging.error("Envoi d'e-mail impossible (%s) : %s", type(e).__name__, e)
        return False
