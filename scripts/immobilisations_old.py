# -*- coding: utf-8 -*-
"""
Module Immobilisations - SMD Global Consulting LLC
Gestion des amortissements, cessions et plan d'investissement
"""
import pandas as pd
import numpy as np
from datetime import datetime


def calculer_amortissement_lineaire(valeur_origine, duree_ans, date_acquisition, date_calcul=None):
    """Calcule le tableau d'amortissement linéaire"""
    if date_calcul is None:
        date_calcul = datetime.now()
    
    taux = 100 / duree_ans
    dotation_annuelle = valeur_origine * taux / 100
    
    tableau = []
    cumul = 0
    
    for annee in range(1, duree_ans + 1):
        date_debut = datetime(date_acquisition.year + annee - 1, date_acquisition.month, date_acquisition.day)
        
        # Prorata première année
        if annee == 1:
            jours_restants = (datetime(date_acquisition.year + 1, 1, 1) - date_acquisition).days
            jours_annee = 365
            dotation = dotation_annuelle * jours_restants / jours_annee
        else:
            dotation = dotation_annuelle
        
        # Dernière année : solde restant
        if annee == duree_ans:
            dotation = valeur_origine - cumul
        
        cumul += dotation
        vnc = valeur_origine - cumul
        
        statut = "✅ Actif"
        if date_calcul.year > date_acquisition.year + annee - 1:
            statut = "✅ Passé"
        elif date_calcul.year == date_acquisition.year + annee - 1:
            statut = "📍 En cours"
        
        tableau.append({
            'Année': date_acquisition.year + annee - 1,
            'Valeur Origine (€)': round(valeur_origine, 2),
            'Taux (%)': round(taux, 2),
            'Dotation (€)': round(dotation, 2),
            'Amort. Cumulé (€)': round(cumul, 2),
            'VNC (€)': round(max(vnc, 0), 2),
            'Statut': statut
        })
    
    return pd.DataFrame(tableau)


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
    rapport.append("*SMD Global Consulting LLC - Superviseur IA Comptable*")
    return "\n".join(rapport)