# -*- coding: utf-8 -*-
"""Formats de fichiers acceptés pour les balances, FEC et relevés - SMD Global Consulting LLC."""

# Tableurs : Excel récent (.xlsx), Excel avec macros (.xlsm), ancien Excel 97-2003 (.xls), LibreOffice (.ods)
EXT_TABLEUR = ("xlsx", "xlsm", "xls", "ods")
TYPES_TABLEUR_CSV = ["csv", *EXT_TABLEUR]
TYPES_BALANCE = ["csv", "txt", *EXT_TABLEUR]


def est_tableur(nom) -> bool:
    """Vrai pour un fichier tableur (extension insensible à la casse)."""
    return str(nom or "").lower().endswith(tuple("." + e for e in EXT_TABLEUR))
