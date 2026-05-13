# -*- coding: utf-8 -*-
"""
Parseur Intelligent Universel - SMD Consulting
Compatible : Sage, Cegid, EBP, Ciel, ACD, Tiime, Pennylane, QuickBooks, Excel
"""
import pandas as pd
import numpy as np


MOTS_CLES = {
    'CompteNum': [
        'compte', 'numero compte', 'n° compte', 'n°compte', 'compte num',
        'comptenum', 'numero', 'cpt', 'account', 'account number',
        'numéro', 'n compte', 'no compte', 'code compte'
    ],
    'CompteLib': [
        'libelle', 'libellé', 'intitule', 'intitulé', 'designation',
        'description', 'nom compte', 'denomination', 'comptelib',
        'name', 'description compte', 'wording'
    ],
    'Debit': [
        'debit', 'débit', 'doit', 'movement debit', 'mouvement debit',
        'mouvement débit', 'sum debit', 'mvt debit', 'mvts debit'
    ],
    'Credit': [
        'credit', 'crédit', 'avoir', 'movement credit', 'mouvement credit',
        'mouvement crédit', 'sum credit', 'mvt credit', 'mvts credit'
    ],
    'SoldeDebiteur': [
        'solde debiteur', 'solde débiteur', 'solde debit', 'solde débit',
        'sd', 'balance debit', 'sld debit', 'sld débit'
    ],
    'SoldeCrediteur': [
        'solde crediteur', 'solde créditeur', 'solde credit', 'solde crédit',
        'sc', 'balance credit', 'sld credit', 'sld crédit'
    ]
}


def detecter_format(df_raw):
    formats_indicateurs = {
        'Sage': ['sage', 'darling sarl'],
        'Cegid': ['cegid', 'quadratus', 'expert'],
        'EBP': ['ebp'],
        'Ciel': ['ciel'],
        'ACD': ['acd', 'agiris'],
        'Tiime': ['tiime'],
        'Pennylane': ['pennylane'],
        'QuickBooks': ['quickbooks', 'intuit']
    }
    
    contenu_debut = ""
    for idx in range(min(10, len(df_raw))):
        contenu_debut += " ".join(str(v).lower() for v in df_raw.iloc[idx].fillna('').values)
    
    for nom_format, indicateurs in formats_indicateurs.items():
        for ind in indicateurs:
            if ind in contenu_debut:
                return nom_format
    
    return 'Standard'


def detecter_ligne_entete(df_raw, max_lignes=30):
    meilleur_score = 0
    meilleure_ligne = None
    
    for idx in range(min(max_lignes, len(df_raw))):
        ligne = df_raw.iloc[idx].fillna('').astype(str).str.lower()
        contenu_ligne = ' '.join(ligne.values)
        
        score = 0
        if any(mc in contenu_ligne for mc in MOTS_CLES['CompteNum']):
            score += 3
        if any(mc in contenu_ligne for mc in MOTS_CLES['CompteLib']):
            score += 2
        if any(mc in contenu_ligne for mc in MOTS_CLES['Debit']):
            score += 2
        if any(mc in contenu_ligne for mc in MOTS_CLES['Credit']):
            score += 2
        
        if score > meilleur_score:
            meilleur_score = score
            meilleure_ligne = idx
    
    return meilleure_ligne if meilleur_score >= 3 else None


def identifier_colonne(nom_colonne, type_colonne):
    nom_lower = str(nom_colonne).lower().strip()
    for mot_cle in MOTS_CLES.get(type_colonne, []):
        if mot_cle in nom_lower:
            return True
    return False


def detecter_colonnes_numeriques(df, colonnes_utilisees):
    """
    Fallback : détecte les colonnes numériques non encore mappées.
    Retourne une liste triée par score (plus de valeurs numériques = score élevé).
    """
    candidats = []
    for col in df.columns:
        if col in colonnes_utilisees:
            continue
        try:
            serie = df[col].astype(str).str.replace(' ', '').str.replace(',', '.')
            nb_numeriques = pd.to_numeric(serie, errors='coerce').notna().sum()
            ratio = nb_numeriques / max(len(df), 1)
            if ratio > 0.3:
                candidats.append((col, nb_numeriques))
        except:
            pass
    candidats.sort(key=lambda x: x[1], reverse=True)
    return [c[0] for c in candidats]


def mapper_colonnes_intelligent(df, info):
    """
    Mappe intelligemment les colonnes vers le format standard.
    Priorité : mots-clés → fallback numérique
    """
    mapping = {}
    colonnes_utilisees = set()
    
    # 1. CompteNum
    for col in df.columns:
        if identifier_colonne(col, 'CompteNum') and col not in colonnes_utilisees:
            mapping[col] = 'CompteNum'
            colonnes_utilisees.add(col)
            break
    
    if 'CompteNum' not in mapping.values():
        for col in df.columns:
            if col not in colonnes_utilisees:
                test_vals = df[col].astype(str).str.match(r'^\d+').sum()
                if test_vals > len(df) * 0.5:
                    mapping[col] = 'CompteNum'
                    colonnes_utilisees.add(col)
                    break
    
    # 2. CompteLib
    for col in df.columns:
        if identifier_colonne(col, 'CompteLib') and col not in colonnes_utilisees:
            mapping[col] = 'CompteLib'
            colonnes_utilisees.add(col)
            break
    
    if 'CompteLib' not in mapping.values():
        for col in df.columns:
            if col not in colonnes_utilisees:
                test_text = df[col].astype(str).str.len().mean()
                if test_text > 5:
                    mapping[col] = 'CompteLib'
                    colonnes_utilisees.add(col)
                    break
    
    # 3. Debit — mots-clés d'abord
    debit_candidats = []
    for col in df.columns:
        if col in colonnes_utilisees:
            continue
        nom_lower = str(col).lower()
        if 'mouvement' in nom_lower and ('débit' in nom_lower or 'debit' in nom_lower):
            debit_candidats.insert(0, col)
        elif identifier_colonne(col, 'Debit') and not identifier_colonne(col, 'SoldeDebiteur'):
            debit_candidats.append(col)
    
    if debit_candidats:
        mapping[debit_candidats[0]] = 'Debit'
        colonnes_utilisees.add(debit_candidats[0])
    
    # 4. Credit — mots-clés d'abord
    credit_candidats = []
    for col in df.columns:
        if col in colonnes_utilisees:
            continue
        nom_lower = str(col).lower()
        if 'mouvement' in nom_lower and ('crédit' in nom_lower or 'credit' in nom_lower):
            credit_candidats.insert(0, col)
        elif identifier_colonne(col, 'Credit') and not identifier_colonne(col, 'SoldeCrediteur'):
            credit_candidats.append(col)
    
    if credit_candidats:
        mapping[credit_candidats[0]] = 'Credit'
        colonnes_utilisees.add(credit_candidats[0])
    
    # 5. FALLBACK NUMÉRIQUE — si Debit ou Credit non détectés par mots-clés
    if 'Debit' not in mapping.values() or 'Credit' not in mapping.values():
        cols_numeriques = detecter_colonnes_numeriques(df, colonnes_utilisees)
        
        if 'Debit' not in mapping.values() and len(cols_numeriques) > 0:
            col_debit = cols_numeriques.pop(0)
            mapping[col_debit] = 'Debit'
            colonnes_utilisees.add(col_debit)
        
        if 'Credit' not in mapping.values() and len(cols_numeriques) > 0:
            col_credit = cols_numeriques.pop(0)
            mapping[col_credit] = 'Credit'
            colonnes_utilisees.add(col_credit)
    
    # 6. Soldes
    for col in df.columns:
        if col in colonnes_utilisees:
            continue
        if identifier_colonne(col, 'SoldeDebiteur'):
            mapping[col] = 'SoldeDebiteur'
            colonnes_utilisees.add(col)
            break
    
    for col in df.columns:
        if col in colonnes_utilisees:
            continue
        if identifier_colonne(col, 'SoldeCrediteur'):
            mapping[col] = 'SoldeCrediteur'
            colonnes_utilisees.add(col)
            break
    
    info['colonnes_mappees'] = mapping
    return df.rename(columns=mapping)


def parser_balance_intelligent(fichier):
    """
    Parse intelligemment une balance, quel que soit le logiciel.
    Returns:
        df_propre: DataFrame standardisé
        info: Informations sur le parsing
    """
    info = {
        'format_detecte': 'Inconnu',
        'ligne_entete': None,
        'nb_lignes_donnees': 0,
        'colonnes_mappees': {},
        'colonnes_manquantes': []
    }
    
    if hasattr(fichier, 'name') and fichier.name.endswith('xlsx'):
        df_raw = pd.read_excel(fichier, header=None)
    else:
        try:
            df_raw = pd.read_csv(fichier, sep=';', encoding='utf-8', header=None)
        except:
            fichier.seek(0)
            df_raw = pd.read_csv(fichier, sep=',', encoding='utf-8', header=None)
    
    info['format_detecte'] = detecter_format(df_raw)
    
    ligne_entete = detecter_ligne_entete(df_raw)
    if ligne_entete is None:
        ligne_entete = 0
    info['ligne_entete'] = ligne_entete
    
    en_tetes = df_raw.iloc[ligne_entete].fillna('').astype(str).tolist()
    
    if ligne_entete > 0:
        ligne_precedente = df_raw.iloc[ligne_entete - 1].fillna('').astype(str).tolist()
        en_tetes_combines = []
        for prev, curr in zip(ligne_precedente, en_tetes):
            prev = prev.strip()
            curr = curr.strip()
            if prev and prev != 'nan' and curr and curr != 'nan':
                en_tetes_combines.append(f"{prev} {curr}")
            elif curr and curr != 'nan':
                en_tetes_combines.append(curr)
            elif prev and prev != 'nan':
                en_tetes_combines.append(prev)
            else:
                en_tetes_combines.append(f"col_{len(en_tetes_combines)}")
        en_tetes = en_tetes_combines
    
    df_donnees = df_raw.iloc[ligne_entete + 1:].copy()
    df_donnees.columns = en_tetes[:len(df_donnees.columns)]
    df_donnees = df_donnees.dropna(how='all').reset_index(drop=True)
    
    df_propre = mapper_colonnes_intelligent(df_donnees, info)
    
    colonnes_essentielles = ['CompteNum', 'Debit', 'Credit']
    info['colonnes_manquantes'] = [
        c for c in colonnes_essentielles 
        if c not in df_propre.columns
    ]
    
    df_propre = nettoyer_balance(df_propre)
    info['nb_lignes_donnees'] = len(df_propre)
    
    return df_propre, info


def nettoyer_balance(df):
    """Supprime lignes de totaux et regroupements"""
    if 'CompteNum' in df.columns:
        df = df[df['CompteNum'].notna()]
        df = df[df['CompteNum'].astype(str).str.strip() != '']
        df = df[~df['CompteNum'].astype(str).str.startswith('**')]
        df = df[~df['CompteNum'].astype(str).str.lower().str.startswith('total')]
    return df.reset_index(drop=True)
