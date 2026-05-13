# -*- coding: utf-8 -*-
"""
Parseur Intelligent Universel v2.0 - SMD Consulting
Compatible : Sage, Cegid, EBP, Ciel, ACD, Tiime, Pennylane, QuickBooks, Excel
5 couches de robustesse : Encodage → Séparateur → En-tête → Mapping → Validation
"""
import pandas as pd
import numpy as np
import chardet
import io
from datetime import datetime


# =============================================================================
# COUCHE 1 — DÉTECTION ENCODAGE AUTOMATIQUE
# =============================================================================

def detecter_encodage(fichier):
    """
    Détecte automatiquement l'encodage du fichier.
    Couvre : UTF-8, ISO-8859-1, Windows-1252, UTF-16
    """
    encodages_a_tester = [
        'utf-8', 'utf-8-sig', 'iso-8859-1',
        'windows-1252', 'latin-1', 'utf-16'
    ]
    
    try:
        contenu_brut = fichier.read()
        fichier.seek(0)
        
        # Détection automatique avec chardet
        detection = chardet.detect(contenu_brut)
        encodage_detecte = detection.get('encoding', 'utf-8')
        confiance = detection.get('confidence', 0)
        
        if confiance > 0.7 and encodage_detecte:
            return encodage_detecte, confiance
        
        # Fallback : tester manuellement
        for enc in encodages_a_tester:
            try:
                contenu_brut.decode(enc)
                return enc, 0.5
            except (UnicodeDecodeError, LookupError):
                continue
                
    except Exception:
        pass
    
    return 'utf-8', 0.3


# =============================================================================
# COUCHE 2 — DÉTECTION SÉPARATEUR AUTOMATIQUE
# =============================================================================

def detecter_separateur(fichier, encodage='utf-8'):
    """
    Détecte automatiquement le séparateur CSV.
    Teste : ; , \t | espace
    """
    separateurs = [';', ',', '\t', '|', ' ']
    
    try:
        contenu = fichier.read().decode(encodage, errors='replace')
        fichier.seek(0)
        
        # Prendre les 5 premières lignes
        lignes = contenu.split('\n')[:5]
        
        scores = {}
        for sep in separateurs:
            counts = [ligne.count(sep) for ligne in lignes if ligne.strip()]
            if counts:
                # Bon séparateur = nombre constant et élevé
                moyenne = sum(counts) / len(counts)
                variance = sum((c - moyenne) ** 2 for c in counts) / len(counts)
                if moyenne > 0:
                    scores[sep] = moyenne / (1 + variance)
        
        if scores:
            meilleur = max(scores, key=scores.get)
            return meilleur
            
    except Exception:
        pass
    
    return ';'


# =============================================================================
# MOTS-CLÉS ÉTENDUS
# =============================================================================

MOTS_CLES = {
    'CompteNum': [
        'compte', 'numero compte', 'n° compte', 'n°compte', 'compte num',
        'comptenum', 'numero', 'cpt', 'account', 'account number',
        'numéro', 'n compte', 'no compte', 'code compte', 'num cpt',
        'code', 'num', 'pcg', 'plan comptable', 'racine'
    ],
    'CompteLib': [
        'libelle', 'libellé', 'intitule', 'intitulé', 'designation',
        'description', 'nom compte', 'denomination', 'comptelib',
        'name', 'description compte', 'wording', 'titre', 'label',
        'intitulé compte', 'nom', 'raison'
    ],
    'Debit': [
        'debit', 'débit', 'doit', 'mvt debit', 'mvts debit',
        'mouvement débit', 'mouvement debit', 'mouvements débit',
        'sum debit', 'total debit', 'cumul debit', 'flux debit',
        'montant débit', 'montant debit', 'dt', 'déb', 'deb',
        'period debit', 'période débit', 'mvt deb'
    ],
    'Credit': [
        'credit', 'crédit', 'avoir', 'mvt credit', 'mvts credit',
        'mouvement crédit', 'mouvement credit', 'mouvements crédit',
        'sum credit', 'total credit', 'cumul credit', 'flux credit',
        'montant crédit', 'montant credit', 'ct', 'cré', 'cre',
        'period credit', 'période crédit', 'mvt cre'
    ],
    'SoldeDebiteur': [
        'solde debiteur', 'solde débiteur', 'solde debit', 'solde débit',
        'sd', 'balance debit', 'sld debit', 'sld débit', 'sold deb',
        'solde d', 'sol deb'
    ],
    'SoldeCrediteur': [
        'solde crediteur', 'solde créditeur', 'solde credit', 'solde crédit',
        'sc', 'balance credit', 'sld credit', 'sld crédit', 'sold cre',
        'solde c', 'sol cre'
    ]
}

FORMATS_LOGICIELS = {
    'Sage': ['sage', 'darling', 'sage 50', 'sage 100', 'i7'],
    'Cegid': ['cegid', 'quadratus', 'expert', 'loop', 'cegid y2'],
    'EBP': ['ebp', 'ebp compta', 'ebp gestion'],
    'Ciel': ['ciel', 'ciel compta', 'ciel evolution'],
    'ACD': ['acd', 'agiris', 'ibiza'],
    'Tiime': ['tiime'],
    'Pennylane': ['pennylane'],
    'QuickBooks': ['quickbooks', 'intuit', 'qbo'],
    'Cegid Expert': ['expert comptable', 'cegid expert'],
    'Myunisoft': ['myunisoft', 'myu'],
    'Fulll': ['fulll'],
}


# =============================================================================
# COUCHE 3 — DÉTECTION LIGNE D'EN-TÊTE AMÉLIORÉE
# =============================================================================

def detecter_format(df_raw):
    """Détecte le logiciel source"""
    contenu_debut = ""
    for idx in range(min(15, len(df_raw))):
        contenu_debut += " ".join(
            str(v).lower() for v in df_raw.iloc[idx].fillna('').values
        )
    
    for nom_format, indicateurs in FORMATS_LOGICIELS.items():
        for ind in indicateurs:
            if ind in contenu_debut:
                return nom_format
    
    return 'Standard'


def score_ligne_entete(ligne_series):
    """
    Calcule un score pour déterminer si une ligne est un en-tête.
    Critères : mots-clés comptables, longueur texte, pas de valeurs numériques pures
    """
    score = 0
    contenu = ' '.join(ligne_series.fillna('').astype(str).str.lower().values)
    
    # Présence de mots-clés comptables
    for type_col, mots in MOTS_CLES.items():
        for mot in mots:
            if mot in contenu:
                poids = 3 if type_col in ['CompteNum', 'Debit', 'Credit'] else 2
                score += poids
                break
    
    # Cellules contenant du texte (pas des nombres)
    nb_texte = sum(
        1 for v in ligne_series.fillna('')
        if str(v).strip() and not str(v).strip().replace('.', '').replace(',', '').replace('-', '').isdigit()
    )
    score += nb_texte * 0.5
    
    # Pénalité si beaucoup de valeurs numériques pures
    nb_numerique = sum(
        1 for v in ligne_series.fillna('')
        if str(v).strip().replace('.', '').replace(',', '').replace('-', '').isdigit()
        and len(str(v).strip()) > 3
    )
    score -= nb_numerique * 2
    
    return score


def detecter_ligne_entete(df_raw, max_lignes=40):
    """
    Détecte la ligne d'en-tête avec scoring amélioré.
    """
    meilleur_score = 0
    meilleure_ligne = 0
    
    for idx in range(min(max_lignes, len(df_raw))):
        score = score_ligne_entete(df_raw.iloc[idx])
        if score > meilleur_score:
            meilleur_score = score
            meilleure_ligne = idx
    
    # Seuil minimum pour valider
    if meilleur_score < 2:
        return 0
    
    return meilleure_ligne


# =============================================================================
# COUCHE 4 — MAPPING COLONNES MULTI-STRATÉGIES
# =============================================================================

def identifier_colonne_par_nom(nom_colonne, type_colonne):
    """Identification par nom de colonne"""
    nom_lower = str(nom_colonne).lower().strip()
    nom_sans_accent = (nom_lower
        .replace('é', 'e').replace('è', 'e').replace('ê', 'e')
        .replace('à', 'a').replace('â', 'a')
        .replace('ù', 'u').replace('û', 'u')
        .replace('î', 'i').replace('ô', 'o')
    )
    
    for mot_cle in MOTS_CLES.get(type_colonne, []):
        mot_sans_accent = (mot_cle
            .replace('é', 'e').replace('è', 'e').replace('ê', 'e')
            .replace('à', 'a').replace('â', 'a')
            .replace('ù', 'u').replace('û', 'u')
            .replace('î', 'i').replace('ô', 'o')
        )
        if mot_sans_accent in nom_sans_accent:
            return True
    return False


def identifier_colonne_par_contenu(serie, type_attendu):
    """
    Identification par contenu de la colonne.
    CompteNum : nombres à 3-8 chiffres
    CompteLib : texte long
    Debit/Credit : nombres décimaux positifs
    """
    serie_propre = serie.dropna().astype(str).str.strip()
    if len(serie_propre) == 0:
        return 0.0
    
    if type_attendu == 'CompteNum':
        # Comptes PCG : 3 à 8 chiffres
        matches = serie_propre.str.match(r'^\d{3,8}$').sum()
        return matches / len(serie_propre)
    
    elif type_attendu == 'CompteLib':
        # Texte avec longueur > 3 caractères et contient des lettres
        matches = serie_propre.apply(
            lambda x: len(x) > 3 and any(c.isalpha() for c in x)
        ).sum()
        return matches / len(serie_propre)
    
    elif type_attendu in ['Debit', 'Credit']:
        # Nombres décimaux (peuvent être 0)
        def est_montant(v):
            try:
                val = float(str(v).replace(',', '.').replace(' ', ''))
                return val >= 0
            except:
                return False
        matches = serie_propre.apply(est_montant).sum()
        return matches / len(serie_propre)
    
    return 0.0


def detecter_colonnes_numeriques_avancee(df, colonnes_utilisees, seuil=0.5):
    """
    Détecte les colonnes numériques avec score de confiance.
    Évite de confondre N° pièce / SIRET avec Débit/Crédit.
    """
    candidats = []
    
    for col in df.columns:
        if col in colonnes_utilisees:
            continue
        
        serie = df[col].dropna().astype(str).str.strip()
        if len(serie) == 0:
            continue
        
        # Convertir en numérique
        serie_num = pd.to_numeric(
            serie.str.replace(',', '.').str.replace(' ', ''),
            errors='coerce'
        )
        
        ratio_numerique = serie_num.notna().sum() / len(serie)
        
        if ratio_numerique < seuil:
            continue
        
        # Pénaliser les colonnes qui ressemblent à des N° de pièce
        # (valeurs entières sans décimales, toutes différentes)
        valeurs_valides = serie_num.dropna()
        est_entier = (valeurs_valides == valeurs_valides.round()).all()
        toutes_differentes = valeurs_valides.nunique() == len(valeurs_valides)
        
        # Score : plus de décimales = plus probablement un montant
        nb_decimales = (valeurs_valides != valeurs_valides.round()).sum()
        score_montant = nb_decimales / max(len(valeurs_valides), 1)
        
        # Si entiers tous différents → probablement N° pièce, pas montant
        if est_entier and toutes_differentes and score_montant == 0:
            continue
        
        score_final = ratio_numerique * (1 + score_montant)
        candidats.append((col, score_final))
    
    candidats.sort(key=lambda x: x[1], reverse=True)
    return [c[0] for c in candidats]


def mapper_colonnes_intelligent(df, info):
    """
    Mapping multi-stratégies :
    1. Par nom de colonne (mots-clés)
    2. Par contenu de colonne
    3. Fallback numérique intelligent
    """
    mapping = {}
    colonnes_utilisees = set()
    scores_confiance = {}
    
    # ── STRATÉGIE 1 : Mapping par nom ──
    
    # CompteNum
    for col in df.columns:
        if col in colonnes_utilisees:
            continue
        if identifier_colonne_par_nom(col, 'CompteNum'):
            mapping[col] = 'CompteNum'
            colonnes_utilisees.add(col)
            scores_confiance['CompteNum'] = 'nom'
            break
    
    # CompteLib
    for col in df.columns:
        if col in colonnes_utilisees:
            continue
        if identifier_colonne_par_nom(col, 'CompteLib'):
            mapping[col] = 'CompteLib'
            colonnes_utilisees.add(col)
            scores_confiance['CompteLib'] = 'nom'
            break
    
    # Debit
    debit_candidats = []
    for col in df.columns:
        if col in colonnes_utilisees:
            continue
        nom_lower = str(col).lower()
        if 'mouvement' in nom_lower and ('débit' in nom_lower or 'debit' in nom_lower):
            debit_candidats.insert(0, col)
        elif identifier_colonne_par_nom(col, 'Debit') and not identifier_colonne_par_nom(col, 'SoldeDebiteur'):
            debit_candidats.append(col)
    
    if debit_candidats:
        mapping[debit_candidats[0]] = 'Debit'
        colonnes_utilisees.add(debit_candidats[0])
        scores_confiance['Debit'] = 'nom'
    
    # Credit
    credit_candidats = []
    for col in df.columns:
        if col in colonnes_utilisees:
            continue
        nom_lower = str(col).lower()
        if 'mouvement' in nom_lower and ('crédit' in nom_lower or 'credit' in nom_lower):
            credit_candidats.insert(0, col)
        elif identifier_colonne_par_nom(col, 'Credit') and not identifier_colonne_par_nom(col, 'SoldeCrediteur'):
            credit_candidats.append(col)
    
    if credit_candidats:
        mapping[credit_candidats[0]] = 'Credit'
        colonnes_utilisees.add(credit_candidats[0])
        scores_confiance['Credit'] = 'nom'
    
    # ── STRATÉGIE 2 : Mapping par contenu ──
    
    if 'CompteNum' not in mapping.values():
        meilleur_score = 0
        meilleure_col = None
        for col in df.columns:
            if col in colonnes_utilisees:
                continue
            score = identifier_colonne_par_contenu(df[col], 'CompteNum')
            if score > meilleur_score and score > 0.5:
                meilleur_score = score
                meilleure_col = col
        if meilleure_col:
            mapping[meilleure_col] = 'CompteNum'
            colonnes_utilisees.add(meilleure_col)
            scores_confiance['CompteNum'] = f'contenu ({meilleur_score:.0%})'
    
    if 'CompteLib' not in mapping.values():
        meilleur_score = 0
        meilleure_col = None
        for col in df.columns:
            if col in colonnes_utilisees:
                continue
            score = identifier_colonne_par_contenu(df[col], 'CompteLib')
            if score > meilleur_score and score > 0.4:
                meilleur_score = score
                meilleure_col = col
        if meilleure_col:
            mapping[meilleure_col] = 'CompteLib'
            colonnes_utilisees.add(meilleure_col)
            scores_confiance['CompteLib'] = f'contenu ({meilleur_score:.0%})'
    
    # ── STRATÉGIE 3 : Fallback numérique intelligent ──
    
    if 'Debit' not in mapping.values() or 'Credit' not in mapping.values():
        cols_numeriques = detecter_colonnes_numeriques_avancee(df, colonnes_utilisees)
        
        if 'Debit' not in mapping.values() and cols_numeriques:
            col = cols_numeriques.pop(0)
            mapping[col] = 'Debit'
            colonnes_utilisees.add(col)
            scores_confiance['Debit'] = 'fallback numérique'
        
        if 'Credit' not in mapping.values() and cols_numeriques:
            col = cols_numeriques.pop(0)
            mapping[col] = 'Credit'
            colonnes_utilisees.add(col)
            scores_confiance['Credit'] = 'fallback numérique'
    
    # ── Soldes ──
    for col in df.columns:
        if col in colonnes_utilisees:
            continue
        if identifier_colonne_par_nom(col, 'SoldeDebiteur'):
            mapping[col] = 'SoldeDebiteur'
            colonnes_utilisees.add(col)
            break
    
    for col in df.columns:
        if col in colonnes_utilisees:
            continue
        if identifier_colonne_par_nom(col, 'SoldeCrediteur'):
            mapping[col] = 'SoldeCrediteur'
            colonnes_utilisees.add(col)
            break
    
    info['colonnes_mappees'] = mapping
    info['scores_confiance'] = scores_confiance
    return df.rename(columns=mapping)


# =============================================================================
# COUCHE 5 — VALIDATION ET CORRECTION DES DONNÉES
# =============================================================================

def valider_et_corriger(df):
    """
    Valide et corrige les données après mapping.
    - Nettoie les montants (virgules, espaces, symboles)
    - Vérifie la cohérence des comptes PCG
    - Détecte les lignes de totaux parasites
    """
    # Nettoyer CompteNum
    if 'CompteNum' in df.columns:
        df['CompteNum'] = (df['CompteNum']
            .astype(str)
            .str.strip()
            .str.replace(r'[^\d]', '', regex=True)
        )
        # Supprimer lignes vides ou invalides
        df = df[df['CompteNum'].str.len() >= 2]
        df = df[~df['CompteNum'].str.lower().str.startswith('total')]
        df = df[~df['CompteNum'].str.startswith('**')]
    
    # Nettoyer montants Debit/Credit
    for col in ['Debit', 'Credit', 'SoldeDebiteur', 'SoldeCrediteur']:
        if col in df.columns:
            df[col] = (df[col]
                .astype(str)
                .str.replace(' ', '')
                .str.replace('\xa0', '')
                .str.replace(',', '.')
                .str.replace(r'[^\d.\-]', '', regex=True)
            )
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Supprimer lignes où tout est NaN
    df = df.dropna(how='all')
    
    return df.reset_index(drop=True)


# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def parser_balance_intelligent(fichier):
    """
    Parse intelligemment une balance, quel que soit le logiciel.
    5 couches : Encodage → Séparateur → En-tête → Mapping → Validation
    
    Returns:
        df_propre : DataFrame standardisé et validé
        info : Informations détaillées sur le parsing
    """
    info = {
        'format_detecte': 'Inconnu',
        'encodage': 'utf-8',
        'separateur': ';',
        'ligne_entete': 0,
        'nb_lignes_donnees': 0,
        'colonnes_mappees': {},
        'scores_confiance': {},
        'colonnes_manquantes': []
    }

    # ── COUCHE 1 : Encodage ──
    est_excel = hasattr(fichier, 'name') and fichier.name.endswith('xlsx')
    
    if not est_excel:
        encodage, confiance = detecter_encodage(fichier)
        info['encodage'] = encodage
    
    # ── COUCHE 2 : Séparateur ──
    if not est_excel:
        try:
            separateur = detecter_separateur(fichier, encodage)
            info['separateur'] = separateur
        except Exception:
            separateur = ';'
            info['separateur'] = ';'
    
    # ── Lecture brute ──
    try:
        if est_excel:
            df_raw = pd.read_excel(fichier, header=None)
        else:
            contenu = fichier.read()
            fichier.seek(0)
            df_raw = pd.read_csv(
                io.BytesIO(contenu),
                sep=separateur,
                encoding=encodage,
                header=None,
                dtype=str,
                on_bad_lines='skip'
            )
    except Exception as e:
        # Dernier recours
        try:
            fichier.seek(0)
            df_raw = pd.read_csv(fichier, sep=';', encoding='latin-1', header=None, dtype=str)
        except Exception:
            return pd.DataFrame(), info
    
    # ── COUCHE 3 : Détection format et en-tête ──
    info['format_detecte'] = detecter_format(df_raw)
    ligne_entete = detecter_ligne_entete(df_raw)
    info['ligne_entete'] = ligne_entete
    
    # Construction en-têtes
    en_tetes = df_raw.iloc[ligne_entete].fillna('').astype(str).tolist()
    
    # Gestion en-tête multi-niveaux
    if ligne_entete > 0:
        ligne_precedente = df_raw.iloc[ligne_entete - 1].fillna('').astype(str).tolist()
        en_tetes_combines = []
        for prev, curr in zip(ligne_precedente, en_tetes):
            prev, curr = prev.strip(), curr.strip()
            if prev and prev != 'nan' and curr and curr != 'nan':
                en_tetes_combines.append(f"{prev} {curr}")
            elif curr and curr != 'nan':
                en_tetes_combines.append(curr)
            elif prev and prev != 'nan':
                en_tetes_combines.append(prev)
            else:
                en_tetes_combines.append(f"col_{len(en_tetes_combines)}")
        en_tetes = en_tetes_combines
    
    # Données
    df_donnees = df_raw.iloc[ligne_entete + 1:].copy()
    df_donnees.columns = en_tetes[:len(df_donnees.columns)]
    df_donnees = df_donnees.dropna(how='all').reset_index(drop=True)
    
    # ── COUCHE 4 : Mapping ──
    df_mappe = mapper_colonnes_intelligent(df_donnees, info)
    
    # ── COUCHE 5 : Validation ──
    df_propre = valider_et_corriger(df_mappe)
    
    # Colonnes manquantes
    colonnes_essentielles = ['CompteNum', 'Debit', 'Credit']
    info['colonnes_manquantes'] = [
        c for c in colonnes_essentielles
        if c not in df_propre.columns
    ]
    
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