# -*- coding: utf-8 -*-
"""Module génération bilan"""
import pandas as pd


def generer_bilan(df, date_cloture):
    """Génère un bilan simplifié"""
    # Placeholder - à adapter selon la structure de vos données
    actif = pd.DataFrame({
        'Poste': ['Immobilisations', 'Stocks', 'Créances', 'Trésorerie'],
        'Montant': [10000, 5000, 15000, 8000]
    })
    
    passif = pd.DataFrame({
        'Poste': ['Capital', 'Réserves', 'Dettes', 'Résultat'],
        'Montant': [20000, 5000, 10000, 3000]
    })
    
    return {'actif': actif, 'passif': passif}