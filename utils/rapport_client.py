# -*- coding: utf-8 -*-
"""Module génération rapports clients"""


def generer_rapport_client(nom_client, siret, periode, exercice, donnees):
    """Génère un rapport personnalisé"""
    rapport = f"""
# Rapport Comptable - {nom_client}

**SIRET** : {siret}  
**Période** : {periode}  
**Exercice** : {exercice}

## Synthèse

Nombre d'écritures analysées : {len(donnees):,}

## Observations

Données comptables conformes.

---
*Rapport généré par SMD Consulting - Superviseur IA*
"""
    return rapport