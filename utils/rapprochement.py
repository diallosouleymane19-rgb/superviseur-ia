# -*- coding: utf-8 -*-
"""Module rapprochement bancaire"""
import pandas as pd


def rapprocher_bancaire(df_releve, df_ecritures):
    """Rapproche relevé bancaire et écritures"""
    # Placeholder - logique de matching simplifiée
    rapproches = df_releve.head(0)  # Vide pour l'instant
    non_rapproches = df_releve
    
    return {
        'nb_rapproches': 0,
        'nb_non_rapproches': len(df_releve),
        'rapproches': rapproches,
        'non_rapproches': non_rapproches
    }