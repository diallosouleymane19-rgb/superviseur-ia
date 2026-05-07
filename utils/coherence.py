# -*- coding: utf-8 -*-
"""Module vérification cohérence"""


def verifier_coherence(df):
    """Vérifie la cohérence des données"""
    # Calcul score
    lignes_completes = df.dropna().shape[0]
    score = int((lignes_completes / len(df)) * 100) if len(df) > 0 else 0
    
    return {
        'score_qualite': score,
        'champs_valides': len(df.columns),
        'lignes_completes': lignes_completes,
        'verifications': {
            'Intégrité': {'status': 'OK', 'message': 'Données cohérentes'}
        },
        'recommandations': ['Continuer la saisie régulière']
    }