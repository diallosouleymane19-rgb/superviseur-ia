# -*- coding: utf-8 -*-
"""Module Rapport Client - SMD Consulting"""
import pandas as pd
from datetime import datetime


def analyser_donnees_client(df):
    """Analyse les donnees comptables et calcule les KPIs"""
    if 'CompteNum' not in df.columns:
        return {'erreur': 'Colonne CompteNum manquante', 'chiffre_affaires': 0}
    
    df = df.copy()
    if 'Debit' in df.columns:
        df['_debit'] = pd.to_numeric(df['Debit'].astype(str).str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0)
    else:
        df['_debit'] = 0
    
    if 'Credit' in df.columns:
        df['_credit'] = pd.to_numeric(df['Credit'].astype(str).str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0)
    else:
        df['_credit'] = 0
    
    df['_compte'] = df['CompteNum'].astype(str).str.strip()
    df['_classe'] = df['_compte'].str[0]
    df['_sous_classe'] = df['_compte'].str[:2]
    
    ca = df[df['_sous_classe'] == '70']['_credit'].sum() - df[df['_sous_classe'] == '70']['_debit'].sum()
    
    charges_60 = df[df['_sous_classe'] == '60']['_debit'].sum() - df[df['_sous_classe'] == '60']['_credit'].sum()
    charges_61 = df[df['_sous_classe'] == '61']['_debit'].sum() - df[df['_sous_classe'] == '61']['_credit'].sum()
    charges_62 = df[df['_sous_classe'] == '62']['_debit'].sum() - df[df['_sous_classe'] == '62']['_credit'].sum()
    charges_63 = df[df['_sous_classe'] == '63']['_debit'].sum() - df[df['_sous_classe'] == '63']['_credit'].sum()
    charges_64 = df[df['_sous_classe'] == '64']['_debit'].sum() - df[df['_sous_classe'] == '64']['_credit'].sum()
    
    total_charges = df[df['_classe'] == '6']['_debit'].sum() - df[df['_classe'] == '6']['_credit'].sum()
    total_produits = df[df['_classe'] == '7']['_credit'].sum() - df[df['_classe'] == '7']['_debit'].sum()
    
    resultat_net = total_produits - total_charges
    valeur_ajoutee = total_produits - (charges_60 + charges_61 + charges_62)
    ebe = valeur_ajoutee - charges_63 - charges_64
    
    immobilisations = df[df['_classe'] == '2']['_debit'].sum() - df[df['_classe'] == '2']['_credit'].sum()
    stocks = df[df['_classe'] == '3']['_debit'].sum() - df[df['_classe'] == '3']['_credit'].sum()
    creances = df[df['_sous_classe'] == '41']['_debit'].sum() - df[df['_sous_classe'] == '41']['_credit'].sum()
    tresorerie = df[df['_sous_classe'].isin(['51', '53'])]['_debit'].sum() - df[df['_sous_classe'].isin(['51', '53'])]['_credit'].sum()
    capital = df[df['_sous_classe'] == '10']['_credit'].sum() - df[df['_sous_classe'] == '10']['_debit'].sum()
    dettes_fin = df[df['_sous_classe'] == '16']['_credit'].sum() - df[df['_sous_classe'] == '16']['_debit'].sum()
    dettes_four = df[df['_sous_classe'] == '40']['_credit'].sum() - df[df['_sous_classe'] == '40']['_debit'].sum()
    
    return {
        'chiffre_affaires': ca,
        'total_produits': total_produits,
        'total_charges': total_charges,
        'resultat_net': resultat_net,
        'valeur_ajoutee': valeur_ajoutee,
        'ebe': ebe,
        'masse_salariale': charges_64,
        'immobilisations': immobilisations,
        'stocks': stocks,
        'creances_clients': creances,
        'tresorerie': tresorerie,
        'capital': capital,
        'dettes_financieres': dettes_fin,
        'dettes_fournisseurs': dettes_four,
        'taux_marge_brute': (ebe / ca * 100) if ca > 0 else 0,
        'taux_rentabilite': (resultat_net / ca * 100) if ca > 0 else 0,
        'taux_va': (valeur_ajoutee / ca * 100) if ca > 0 else 0,
        'poids_charges_personnel': (charges_64 / ca * 100) if ca > 0 else 0
    }


def generer_rapport_client(nom_client, siret, periode, exercice, donnees, observations="", objectifs=""):
    """Genere un rapport client professionnel"""
    
    # Analyse
    if not donnees.empty and 'CompteNum' in donnees.columns:
        kpis = analyser_donnees_client(donnees)
    else:
        kpis = None
    
    rapport = []
    
    rapport.append(f"# RAPPORT D'ACTIVITE COMPTABLE")
    rapport.append(f"## {nom_client}")
    rapport.append(f"### Periode : {periode} {exercice}")
    rapport.append(f"")
    rapport.append(f"**Date d'edition** : {datetime.now().strftime('%d/%m/%Y')}")
    rapport.append(f"**SIRET** : {siret if siret else 'Non renseigne'}")
    rapport.append("")
    rapport.append("---")
    rapport.append("")
    
    rapport.append("## SYNTHESE EXECUTIVE")
    rapport.append("")
    
    if kpis and kpis.get('chiffre_affaires', 0) > 0:
        ca = kpis['chiffre_affaires']
        rn = kpis['resultat_net']
        ebe = kpis['ebe']
        
        rapport.append(f"L'analyse de la periode {periode} {exercice} pour **{nom_client}** revele :")
        rapport.append("")
        rapport.append(f"- **Chiffre d'affaires** : {ca:,.0f} EUR")
        rapport.append(f"- **Resultat net** : {rn:,.0f} EUR ({kpis['taux_rentabilite']:.1f}% du CA)")
        rapport.append(f"- **EBE** : {ebe:,.0f} EUR ({kpis['taux_marge_brute']:.1f}% du CA)")
        rapport.append(f"- **Valeur ajoutee** : {kpis['valeur_ajoutee']:,.0f} EUR ({kpis['taux_va']:.1f}% du CA)")
        rapport.append("")
        
        if rn > 0 and ebe > 0:
            rapport.append("**Situation saine** : Resultats positifs sur l'exercice")
        elif rn > 0 and ebe < 0:
            rapport.append("**Situation fragile** : Resultat positif mais EBE negatif")
        elif rn < 0 and ebe > 0:
            rapport.append("**Vigilance** : Resultat net negatif malgre EBE positif")
        else:
            rapport.append("**Situation preoccupante** : Audit approfondi recommande")
    else:
        rapport.append("*Donnees insuffisantes pour synthese detaillee*")
    
    rapport.append("")
    rapport.append("---")
    rapport.append("")
    
    if kpis and kpis.get('chiffre_affaires', 0) > 0:
        rapport.append("## INDICATEURS CLES")
        rapport.append("")
        rapport.append("### Compte de Resultat")
        rapport.append("")
        rapport.append("| Indicateur | Montant (EUR) | % du CA |")
        rapport.append("|------------|---------------|---------|")
        ca = kpis['chiffre_affaires']
        rapport.append(f"| Chiffre d'affaires | {ca:,.0f} | 100% |")
        rapport.append(f"| Total produits | {kpis['total_produits']:,.0f} | {kpis['total_produits']/ca*100:.1f}% |")
        rapport.append(f"| Total charges | {kpis['total_charges']:,.0f} | {kpis['total_charges']/ca*100:.1f}% |")
        rapport.append(f"| Resultat net | {kpis['resultat_net']:,.0f} | {kpis['taux_rentabilite']:.1f}% |")
        rapport.append(f"| Valeur ajoutee | {kpis['valeur_ajoutee']:,.0f} | {kpis['taux_va']:.1f}% |")
        rapport.append(f"| EBE | {kpis['ebe']:,.0f} | {kpis['taux_marge_brute']:.1f}% |")
        rapport.append(f"| Masse salariale | {kpis['masse_salariale']:,.0f} | {kpis['poids_charges_personnel']:.1f}% |")
        rapport.append("")
        
        rapport.append("### Bilan")
        rapport.append("")
        rapport.append("| Poste | Montant (EUR) |")
        rapport.append("|-------|---------------|")
        rapport.append(f"| Immobilisations | {kpis['immobilisations']:,.0f} |")
        rapport.append(f"| Stocks | {kpis['stocks']:,.0f} |")
        rapport.append(f"| Creances clients | {kpis['creances_clients']:,.0f} |")
        rapport.append(f"| Tresorerie | {kpis['tresorerie']:,.0f} |")
        rapport.append(f"| Capital | {kpis['capital']:,.0f} |")
        rapport.append(f"| Dettes financieres | {kpis['dettes_financieres']:,.0f} |")
        rapport.append(f"| Dettes fournisseurs | {kpis['dettes_fournisseurs']:,.0f} |")
        rapport.append("")
        rapport.append("---")
        rapport.append("")
    
    rapport.append("## ANALYSE DU CABINET")
    rapport.append("")
    
    if kpis and kpis.get('chiffre_affaires', 0) > 0:
        if kpis['taux_rentabilite'] > 10:
            rapport.append("- **Rentabilite excellente** : marge nette > 10%")
        elif kpis['taux_rentabilite'] > 5:
            rapport.append("- **Bonne rentabilite** : marge nette satisfaisante")
        elif kpis['taux_rentabilite'] > 0:
            rapport.append("- **Rentabilite faible** : marges a renforcer")
        else:
            rapport.append("- **Activite deficitaire** : actions correctives urgentes")
        
        if kpis['taux_va'] > 30:
            rapport.append("- **Forte valeur ajoutee** : modele economique robuste")
        elif kpis['taux_va'] < 15:
            rapport.append("- **Faible valeur ajoutee** : revoir la chaine de valeur")
        
        if kpis['poids_charges_personnel'] > 50:
            rapport.append("- **Charges personnel elevees** (>50% CA) : optimiser productivite")
        
        if kpis['tresorerie'] < 0:
            rapport.append("- **Tresorerie negative** : risque d'illiquidite")
    
    rapport.append("")
    rapport.append("---")
    rapport.append("")
    
    if observations:
        rapport.append("## OBSERVATIONS PARTICULIERES")
        rapport.append("")
        rapport.append(observations)
        rapport.append("")
        rapport.append("---")
        rapport.append("")
    
    rapport.append("## RECOMMANDATIONS DU CABINET")
    rapport.append("")
    rapport.append("- **Suivi mensuel** : Tableau de bord mensuel des KPIs cles")
    rapport.append("- **Optimisation fiscale** : Verifier eligibilite CIR, CII, JEI")
    rapport.append("- **Tresorerie** : Plan previsionnel a 3 mois")
    rapport.append("- **Audit interne** : Audit annuel des processus comptables")
    rapport.append("")
    
    if objectifs:
        rapport.append("---")
        rapport.append("")
        rapport.append("## OBJECTIFS PROCHAINE PERIODE")
        rapport.append("")
        rapport.append(objectifs)
        rapport.append("")
    
    rapport.append("---")
    rapport.append("")
    rapport.append("*Rapport genere par SMD Consulting - Superviseur IA Comptable*")
    rapport.append(f"*(c) {datetime.now().year} - Tous droits reserves*")
    
    return "\n".join(rapport)