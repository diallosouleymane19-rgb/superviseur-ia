# -*- coding: utf-8 -*-
"""
Module Compte de Resultat Professionnel - SMD Consulting
Calcul des SIG (Soldes Intermediaires de Gestion) selon PCG francais
Pour Cabinets, DAF et Dirigeants
"""
import pandas as pd
import numpy as np
from datetime import datetime


# Mapping des comptes PCG vers les rubriques du compte de resultat
RUBRIQUES_PCG = {
    # PRODUITS
    '70': 'Ventes de marchandises et services',
    '701': 'Ventes de produits finis',
    '706': 'Prestations de services',
    '707': 'Ventes de marchandises',
    '708': 'Produits des activites annexes',
    '71': 'Production stockee',
    '72': 'Production immobilisee',
    '74': 'Subventions d\'exploitation',
    '75': 'Autres produits de gestion courante',
    '76': 'Produits financiers',
    '77': 'Produits exceptionnels',
    '78': 'Reprises sur amortissements et provisions',
    '79': 'Transferts de charges',
    
    # CHARGES
    '60': 'Achats',
    '601': 'Achats stockes - Matieres premieres',
    '607': 'Achats de marchandises',
    '603': 'Variation des stocks',
    '61': 'Services exterieurs',
    '62': 'Autres services exterieurs',
    '63': 'Impots et taxes',
    '64': 'Charges de personnel',
    '641': 'Salaires bruts',
    '645': 'Charges sociales',
    '65': 'Autres charges de gestion courante',
    '66': 'Charges financieres',
    '67': 'Charges exceptionnelles',
    '68': 'Dotations aux amortissements et provisions',
    '69': 'Impots sur les benefices'
}


def calculer_compte_resultat(df, type_entreprise='Mixte'):
    """
    Calcule le compte de resultat detaille a partir d'une balance
    
    Args:
        df: DataFrame avec colonnes CompteNum, Debit, Credit
        type_entreprise: 'Commerciale', 'Industrielle', 'Services', 'Mixte'
    
    Returns:
        dict: Compte de resultat structure avec SIG et ratios
    """
    # Normaliser les colonnes
    if 'CompteNum' not in df.columns:
        return {'erreur': 'Colonne CompteNum manquante'}
    
    # Conversion numerique
    df = df.copy()
    if 'Debit' in df.columns:
        df['_debit'] = pd.to_numeric(
            df['Debit'].astype(str).str.replace(',', '.').str.replace(' ', ''), 
            errors='coerce'
        ).fillna(0)
    else:
        df['_debit'] = 0
    
    if 'Credit' in df.columns:
        df['_credit'] = pd.to_numeric(
            df['Credit'].astype(str).str.replace(',', '.').str.replace(' ', ''),
            errors='coerce'
        ).fillna(0)
    else:
        df['_credit'] = 0
    
    # Conversion compte en string et extraction classe/sous-classe
    df['_compte'] = df['CompteNum'].astype(str).str.strip()
    df['_classe'] = df['_compte'].str[0]
    df['_sous_classe'] = df['_compte'].str[:2]
    df['_racine_3'] = df['_compte'].str[:3]
    
    resultat = {
        'type_entreprise': type_entreprise,
        'date_calcul': datetime.now().strftime('%d/%m/%Y'),
        'produits': {},
        'charges': {},
        'sig': {},
        'ratios': {},
        'analyse': []
    }
    
    # ===== PRODUITS (Classe 7) =====
    produits_70 = df[df['_sous_classe'] == '70']['_credit'].sum() - df[df['_sous_classe'] == '70']['_debit'].sum()
    produits_71 = df[df['_sous_classe'] == '71']['_credit'].sum() - df[df['_sous_classe'] == '71']['_debit'].sum()
    produits_72 = df[df['_sous_classe'] == '72']['_credit'].sum() - df[df['_sous_classe'] == '72']['_debit'].sum()
    produits_74 = df[df['_sous_classe'] == '74']['_credit'].sum() - df[df['_sous_classe'] == '74']['_debit'].sum()
    produits_75 = df[df['_sous_classe'] == '75']['_credit'].sum() - df[df['_sous_classe'] == '75']['_debit'].sum()
    produits_76 = df[df['_sous_classe'] == '76']['_credit'].sum() - df[df['_sous_classe'] == '76']['_debit'].sum()
    produits_77 = df[df['_sous_classe'] == '77']['_credit'].sum() - df[df['_sous_classe'] == '77']['_debit'].sum()
    produits_78 = df[df['_sous_classe'] == '78']['_credit'].sum() - df[df['_sous_classe'] == '78']['_debit'].sum()
    produits_79 = df[df['_sous_classe'] == '79']['_credit'].sum() - df[df['_sous_classe'] == '79']['_debit'].sum()
    
    # Detail ventes
    ventes_marchandises = df[df['_racine_3'] == '707']['_credit'].sum() - df[df['_racine_3'] == '707']['_debit'].sum()
    ventes_produits = df[df['_racine_3'] == '701']['_credit'].sum() - df[df['_racine_3'] == '701']['_debit'].sum()
    prestations = df[df['_racine_3'] == '706']['_credit'].sum() - df[df['_racine_3'] == '706']['_debit'].sum()
    
    resultat['produits'] = {
        'Ventes marchandises (707)': ventes_marchandises,
        'Ventes produits finis (701)': ventes_produits,
        'Prestations services (706)': prestations,
        'Autres ventes (70)': produits_70 - ventes_marchandises - ventes_produits - prestations,
        'Production stockee (71)': produits_71,
        'Production immobilisee (72)': produits_72,
        'Subventions (74)': produits_74,
        'Autres produits gestion (75)': produits_75,
        'Produits financiers (76)': produits_76,
        'Produits exceptionnels (77)': produits_77,
        'Reprises (78)': produits_78,
        'Transferts charges (79)': produits_79,
    }
    
    # Total chiffre d'affaires
    chiffre_affaires = produits_70
    production_exercice = produits_70 + produits_71 + produits_72
    
    # ===== CHARGES (Classe 6) =====
    achats_marchandises = df[df['_racine_3'] == '607']['_debit'].sum() - df[df['_racine_3'] == '607']['_credit'].sum()
    achats_mp = df[df['_racine_3'] == '601']['_debit'].sum() - df[df['_racine_3'] == '601']['_credit'].sum()
    var_stocks = df[df['_racine_3'] == '603']['_debit'].sum() - df[df['_racine_3'] == '603']['_credit'].sum()
    
    charges_60 = df[df['_sous_classe'] == '60']['_debit'].sum() - df[df['_sous_classe'] == '60']['_credit'].sum()
    charges_61 = df[df['_sous_classe'] == '61']['_debit'].sum() - df[df['_sous_classe'] == '61']['_credit'].sum()
    charges_62 = df[df['_sous_classe'] == '62']['_debit'].sum() - df[df['_sous_classe'] == '62']['_credit'].sum()
    charges_63 = df[df['_sous_classe'] == '63']['_debit'].sum() - df[df['_sous_classe'] == '63']['_credit'].sum()
    charges_64 = df[df['_sous_classe'] == '64']['_debit'].sum() - df[df['_sous_classe'] == '64']['_credit'].sum()
    charges_65 = df[df['_sous_classe'] == '65']['_debit'].sum() - df[df['_sous_classe'] == '65']['_credit'].sum()
    charges_66 = df[df['_sous_classe'] == '66']['_debit'].sum() - df[df['_sous_classe'] == '66']['_credit'].sum()
    charges_67 = df[df['_sous_classe'] == '67']['_debit'].sum() - df[df['_sous_classe'] == '67']['_credit'].sum()
    charges_68 = df[df['_sous_classe'] == '68']['_debit'].sum() - df[df['_sous_classe'] == '68']['_credit'].sum()
    charges_69 = df[df['_sous_classe'] == '69']['_debit'].sum() - df[df['_sous_classe'] == '69']['_credit'].sum()
    
    salaires = df[df['_racine_3'] == '641']['_debit'].sum() - df[df['_racine_3'] == '641']['_credit'].sum()
    charges_sociales = df[df['_racine_3'] == '645']['_debit'].sum() - df[df['_racine_3'] == '645']['_credit'].sum()
    
    resultat['charges'] = {
        'Achats marchandises (607)': achats_marchandises,
        'Achats matieres premieres (601)': achats_mp,
        'Variation stocks (603)': var_stocks,
        'Autres achats (60)': charges_60 - achats_marchandises - achats_mp - var_stocks,
        'Services exterieurs (61)': charges_61,
        'Autres services exterieurs (62)': charges_62,
        'Impots et taxes (63)': charges_63,
        'Salaires bruts (641)': salaires,
        'Charges sociales (645)': charges_sociales,
        'Autres charges personnel (64)': charges_64 - salaires - charges_sociales,
        'Autres charges gestion (65)': charges_65,
        'Charges financieres (66)': charges_66,
        'Charges exceptionnelles (67)': charges_67,
        'Dotations amortissements (68)': charges_68,
        'Impots sur benefices (69)': charges_69,
    }
    
    # ===== CALCUL DES SIG =====
    
    # 1. Marge commerciale
    marge_commerciale = ventes_marchandises - achats_marchandises - var_stocks
    
    # 2. Production de l'exercice
    # Deja calcule plus haut
    
    # 3. Valeur ajoutee
    consommations_externes = charges_61 + charges_62 + (charges_60 - achats_marchandises)
    valeur_ajoutee = marge_commerciale + production_exercice - consommations_externes
    
    # 4. Excedent Brut d'Exploitation (EBE)
    ebe = valeur_ajoutee + produits_74 - charges_63 - charges_64
    
    # 5. Resultat d'exploitation
    resultat_exploitation = ebe + produits_75 + produits_78 + produits_79 - charges_65 - charges_68
    
    # 6. Resultat financier
    resultat_financier = produits_76 - charges_66
    
    # 7. Resultat courant avant impots
    resultat_courant = resultat_exploitation + resultat_financier
    
    # 8. Resultat exceptionnel
    resultat_exceptionnel = produits_77 - charges_67
    
    # 9. Resultat net
    resultat_net = resultat_courant + resultat_exceptionnel - charges_69
    
    resultat['sig'] = {
        'Chiffre d\'affaires': chiffre_affaires,
        'Production de l\'exercice': production_exercice,
        'Marge commerciale': marge_commerciale,
        'Consommations externes': consommations_externes,
        'Valeur ajoutée (VA)': valeur_ajoutee,
        'Excedent Brut d\'Exploitation (EBE)': ebe,
        'Resultat d\'exploitation': resultat_exploitation,
        'Resultat financier': resultat_financier,
        'Resultat courant avant impots': resultat_courant,
        'Resultat exceptionnel': resultat_exceptionnel,
        'Resultat net': resultat_net
    }
    
    # ===== RATIOS DE PERFORMANCE =====
    if chiffre_affaires > 0:
        resultat['ratios'] = {
            'Taux de marge commerciale (%)': (marge_commerciale / ventes_marchandises * 100) if ventes_marchandises > 0 else 0,
            'Taux de valeur ajoutee (%)': (valeur_ajoutee / chiffre_affaires * 100),
            'Taux de marge brute - EBE (%)': (ebe / chiffre_affaires * 100),
            'Taux de rentabilite exploitation (%)': (resultat_exploitation / chiffre_affaires * 100),
            'Taux de rentabilite nette (%)': (resultat_net / chiffre_affaires * 100),
            'Poids charges personnel (%)': (charges_64 / chiffre_affaires * 100),
            'Poids consommations externes (%)': (consommations_externes / chiffre_affaires * 100),
            'Productivite par salarie (€)': valeur_ajoutee  # A diviser par effectif si connu
        }
    
    # ===== ANALYSE QUALITATIVE =====
    if resultat_net > 0:
        resultat['analyse'].append({
            'type': 'OK',
            'message': f'Resultat net BENEFICIAIRE de {resultat_net:,.2f} EUR'
        })
    else:
        resultat['analyse'].append({
            'type': 'WARNING',
            'message': f'Resultat net DEFICITAIRE de {resultat_net:,.2f} EUR'
        })
    
    if ebe > 0:
        resultat['analyse'].append({
            'type': 'OK',
            'message': f'EBE positif : capacite a generer du cash sur l\'activite'
        })
    else:
        resultat['analyse'].append({
            'type': 'CRITIQUE',
            'message': f'EBE negatif : difficulte a couvrir les charges courantes'
        })
    
    if 'Taux de valeur ajoutee (%)' in resultat['ratios']:
        taux_va = resultat['ratios']['Taux de valeur ajoutee (%)']
        if taux_va > 30:
            resultat['analyse'].append({
                'type': 'OK',
                'message': f'Bon taux de valeur ajoutee ({taux_va:.1f}%)'
            })
        elif taux_va < 15:
            resultat['analyse'].append({
                'type': 'WARNING',
                'message': f'Faible taux de valeur ajoutee ({taux_va:.1f}%) - revoir la chaine de valeur'
            })
    
    return resultat


def generer_rapport_compte_resultat(resultat, nom_entreprise="Entreprise", exercice=""):
    """Genere un rapport professionnel du compte de resultat"""
    
    rapport = []
    rapport.append(f"# COMPTE DE RESULTAT - ANALYSE PROFESSIONNELLE")
    rapport.append(f"## {nom_entreprise} - Exercice {exercice}")
    rapport.append(f"*Date d'analyse : {resultat['date_calcul']}*")
    rapport.append(f"*Type d'entreprise : {resultat['type_entreprise']}*\n")
    rapport.append("---\n")
    
    # SOLDES INTERMEDIAIRES DE GESTION
    rapport.append("## 📊 SOLDES INTERMEDIAIRES DE GESTION (SIG)\n")
    rapport.append("| Indicateur | Montant |")
    rapport.append("|------------|---------|")
    for nom, valeur in resultat['sig'].items():
        rapport.append(f"| **{nom}** | {valeur:,.2f} EUR |")
    rapport.append("")
    
    # RATIOS
    if resultat['ratios']:
        rapport.append("## 📈 RATIOS DE PERFORMANCE\n")
        rapport.append("| Ratio | Valeur |")
        rapport.append("|-------|--------|")
        for nom, valeur in resultat['ratios'].items():
            if '€' in nom:
                rapport.append(f"| {nom} | {valeur:,.2f} |")
            else:
                rapport.append(f"| {nom} | {valeur:.2f}% |")
        rapport.append("")
    
    # ANALYSE
    if resultat['analyse']:
        rapport.append("## 💡 ANALYSE QUALITATIVE\n")
        for item in resultat['analyse']:
            symbol = '✅' if item['type'] == 'OK' else '⚠️' if item['type'] == 'WARNING' else '🔴'
            rapport.append(f"- {symbol} {item['message']}")
        rapport.append("")
    
    rapport.append("---")
    rapport.append("*Rapport genere par SMD Consulting - Superviseur IA Comptable*")
    
    return "\n".join(rapport)