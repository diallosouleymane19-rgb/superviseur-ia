# -*- coding: utf-8 -*-
"""Module compte de résultat"""
import pandas as pd


def generer_compte_resultat(df, date_debut, date_fin):
    """Génère un compte de résultat simplifié"""
    # Placeholder
    resultat = pd.DataFrame({
        'Type': ['Produits', 'Produits', 'Charges', 'Charges'],
        'Poste': ['Ventes', 'Autres produits', 'Achats', 'Charges externes'],
        'Montant': [100000, 5000, 60000, 20000]
    })
    
    return resultat