# -*- coding: utf-8 -*-
"""
utils/security.py - SMD Global Consulting LLC
Helpers de securite : sanitisation des entrees utilisateur.
"""
import re
import html


def sanitize_filename(s: str, max_len: int = 80) -> str:
    """
    Nettoie une chaine pour usage sur un nom de fichier.
    Supprime les caracteres de traversee de chemin et les caracteres speciaux.
    """
    if not s:
        return "document"
    # Supprimer les caracteres dangereux pour les chemins
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', s)
    # Supprimer les sequences de traversee de chemin
    s = re.sub(r'\.{2,}', '', s)
    # Supprimer les slashes residuels
    s = s.replace('/', '').replace('\\', '')
    # Remplacer les espaces par underscores
    s = s.replace(' ', '_')
    # Supprimer les caracteres non-ASCII dangereux dans les noms de fichiers
    s = re.sub(r'[^\w\-.]', '_', s)
    # Limiter la longueur
    s = s[:max_len]
    # Fallback si vide apres nettoyage
    return s if s.strip('_') else "document"


def sanitize_html_value(s) -> str:
    """
    Echappe les caracteres HTML dangereux dans une valeur user
    avant insertion dans un bloc unsafe_allow_html.
    """
    return html.escape(str(s), quote=True)


def sanitize_ai_text(s: str) -> str:
    """
    Nettoie le texte venant de l'IA avant affichage HTML.
    Supprime les balises script/style potentielles.
    """
    # Supprimer les balises script et style
    s = re.sub(r'<script[^>]*>.*?</script>', '', s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r'<style[^>]*>.*?</style>', '', s, flags=re.IGNORECASE | re.DOTALL)
    # Supprimer les event handlers onclick, onerror, etc.
    s = re.sub(r'\bon\w+\s*=\s*["\'][^"\']*["\']', '', s, flags=re.IGNORECASE)
    # Supprimer javascript: dans les href
    s = re.sub(r'javascript\s*:', '', s, flags=re.IGNORECASE)
    return s
