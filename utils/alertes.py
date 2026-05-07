# -*- coding: utf-8 -*-
"""Module détection alertes"""


def detecter_alertes(df):
    """Détecte les anomalies dans les données"""
    alertes = []
    
    # Exemple d'alerte
    if len(df) > 10000:
        alertes.append({
            'niveau': 'INFO',
            'titre': 'Volume important',
            'message': f'{len(df):,} écritures analysées'
        })
    
    return alertes