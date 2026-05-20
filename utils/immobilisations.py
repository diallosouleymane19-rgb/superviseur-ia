# -*- coding: utf-8 -*-
"""
Module Immobilisations - SMD Consulting
Gestion des amortissements, cessions et plan d'investissement
"""
import pandas as pd
import numpy as np
from datetime import datetime


import pandas as pd
from datetime import datetime

def calculer_amortissement_lineaire(valeur_origine, duree_ans, date_acquisition):
    """Calcule le tableau d'amortissement linéaire au prorata mensuel"""
    taux = 100 / duree_ans
    
    # 1. Calcul du prorata de la première année (mois d'achat inclus)
    mois_restants = 12 - date_acquisition.month + 1
    annuite_an1 = (valeur_origine * (taux / 100)) * (mois_restants / 12)
    
    # 2. Préparation du tableau
    annees = []
    lignes = []
    vnc = valeur_origine
    amort_cumule = 0
    
    for i in range(duree_ans + 1):
        annee = date_acquisition.year + i
        if i == 0:
            dotation = annuite_an1
        elif i == duree_ans:
            # Solde de la dernière année (ce qui reste pour arriver à 0)
            dotation = valeur_origine - amort_cumule
        else:
            dotation = valeur_origine * (taux / 100)
            
        # Arrondir la dotation pour éviter les problèmes de virgules flottantes
        dotation = round(min(dotation, valeur_origine - amort_cumule), 2)
        
        if dotation <= 0: break
        
        amort_cumule += dotation
        vnc -= dotation
        
        lignes.append({
            "Année": annee,
            "Valeur Origine (€)": valeur_origine,
            "Taux (%)": round(taux, 2),
            "Dotation (€)": dotation,
            "Amort. Cumulé (€)": round(amort_cumule, 2),
            "VNC (€)": round(max(vnc, 0), 2),
            "Statut": "Passé" if annee < datetime.now().year else "En cours" if annee == datetime.now().year else "À venir"
        })
        
    return pd.DataFrame(lignes)

def calculer_amortissement_degressif(valeur_origine, duree_ans, date_acquisition, date_calcul=None):
    """Calcule le tableau d'amortissement dégressif"""
    if date_calcul is None:
        date_calcul = datetime.now()
    
    # Coefficients fiscaux français
    coefficients = {3: 1.25, 4: 1.25, 5: 1.75, 6: 1.75, 7: 2.25, 10: 2.25}
    coeff = 2.25
    for duree_seuil, c in sorted(coefficients.items()):
        if duree_ans <= duree_seuil:
            coeff = c
            break
    
    taux_degressif = (100 / duree_ans) * coeff
    
    tableau = []
    vnc_debut = valeur_origine
    cumul = 0
    
    for annee in range(1, duree_ans + 1):
        annees_restantes = duree_ans - annee + 1
        taux_lineaire_restant = 100 / annees_restantes
        
        # Bascule vers linéaire si plus avantageux
        if taux_lineaire_restant > taux_degressif:
            dotation = vnc_debut / annees_restantes
        else:
            dotation = vnc_debut * taux_degressif / 100
        
        # Prorata première année
        if annee == 1:
            jours_restants = (datetime(date_acquisition.year + 1, 1, 1) - date_acquisition).days
            dotation = dotation * jours_restants / 365
        
        cumul += dotation
        vnc_fin = max(vnc_debut - dotation, 0)
        
        statut = "✅ Passé"
        if date_calcul.year == date_acquisition.year + annee - 1:
            statut = "📍 En cours"
        elif date_calcul.year < date_acquisition.year + annee - 1:
            statut = "🔮 Futur"
        
        tableau.append({
            'Année': date_acquisition.year + annee - 1,
            'VNC Début (€)': round(vnc_debut, 2),
            'Taux Dégressif (%)': round(taux_degressif, 2),
            'Dotation (€)': round(dotation, 2),
            'Amort. Cumulé (€)': round(cumul, 2),
            'VNC Fin (€)': round(vnc_fin, 2),
            'Statut': statut
        })
        
        vnc_debut = vnc_fin
    
    return pd.DataFrame(tableau)


def calculer_cession(valeur_origine, amort_cumule, prix_cession, date_cession, taux_is=25):
    """Calcule la plus ou moins-value de cession"""
    vnc = valeur_origine - amort_cumule
    resultat_cession = prix_cession - vnc
    
    type_resultat = "Plus-value" if resultat_cession > 0 else "Moins-value"
    impot_estime = max(resultat_cession * taux_is / 100, 0) if resultat_cession > 0 else 0
    
    # Écritures comptables
    ecritures = []
    
    # Sortie du bien
    ecritures.append({
        'Compte': '28xx',
        'Libellé': 'Amortissements cumulés',
        'Débit': round(amort_cumule, 2),
        'Crédit': 0
    })
    ecritures.append({
        'Compte': '512',
        'Libellé': 'Banque (prix de cession)',
        'Débit': round(prix_cession, 2),
        'Crédit': 0
    })
    
    if resultat_cession >= 0:
        ecritures.append({
            'Compte': '2xxx',
            'Libellé': 'Immobilisation (valeur origine)',
            'Débit': 0,
            'Crédit': round(valeur_origine, 2)
        })
        ecritures.append({
            'Compte': '775',
            'Libellé': 'Produit de cession',
            'Débit': 0,
            'Crédit': round(prix_cession, 2)
        })
    else:
        ecritures.append({
            'Compte': '675',
            'Libellé': 'Valeur nette comptable cédée',
            'Débit': round(vnc, 2),
            'Crédit': 0
        })
        ecritures.append({
            'Compte': '2xxx',
            'Libellé': 'Immobilisation (valeur origine)',
            'Débit': 0,
            'Crédit': round(valeur_origine, 2)
        })
    
    return {
        'valeur_origine': valeur_origine,
        'amort_cumule': amort_cumule,
        'vnc': round(vnc, 2),
        'prix_cession': prix_cession,
        'resultat_cession': round(resultat_cession, 2),
        'type_resultat': type_resultat,
        'impot_estime': round(impot_estime, 2),
        'ecritures': pd.DataFrame(ecritures)
    }


def generer_rapport_immobilisation(bien, tableau, mode):
    """Génère un rapport professionnel"""
    rapport = [f"# TABLEAU D'AMORTISSEMENT — {bien}"]
    rapport.append(f"Mode : {mode}")
    rapport.append(f"*Généré le {datetime.now().strftime('%d/%m/%Y')}*\n---\n")
    
    for _, row in tableau.iterrows():
        rapport.append(
            f"- {int(row['Année'])} : Dotation {row.get('Dotation (€)', 0):,.2f} € | "
            f"VNC {row.get('VNC (€)', row.get('VNC Fin (€)', 0)):,.2f} € | {row['Statut']}"
        )
    
    rapport.append("\n---")
    rapport.append("*SMD Consulting - Superviseur IA Comptable*")
    return "\n".join(rapport)
def generer_ecritures_amortissement(nom_bien, tableau, exercice_courant=None):
    """Génère les écritures comptables d'amortissement"""
    if exercice_courant is None:
        exercice_courant = datetime.now().year
    
    ecritures = []
    
    for _, row in tableau.iterrows():
        annee = int(row['Année'])
        dotation = row['Dotation (€)']
        
        if dotation > 0:
            ecritures.append({
                'Année': annee,
                'Date': f"31/12/{annee}",
                'Compte Débit': '6811',
                'Libellé Débit': f"Dotation amort. — {nom_bien}",
                'Débit (€)': round(dotation, 2),
                'Compte Crédit': '28xx',
                'Libellé Crédit': f"Amort. {nom_bien}",
                'Crédit (€)': round(dotation, 2),
                'Statut': row['Statut']
            })
    
    return pd.DataFrame(ecritures)
