# -*- coding: utf-8 -*-
"""Module Rapprochement Bancaire - SMD Consulting"""
import pandas as pd
from datetime import datetime, timedelta


def normaliser_montant(serie):
    return pd.to_numeric(
        serie.astype(str).str.replace(',', '.').str.replace(' ', '').str.replace('€', ''),
        errors='coerce'
    ).fillna(0)


def normaliser_date(serie):
    return pd.to_datetime(serie, errors='coerce', dayfirst=True)


def calculer_similarite_libelle(lib1, lib2):
    if pd.isna(lib1) or pd.isna(lib2):
        return 0
    lib1 = str(lib1).lower().strip()
    lib2 = str(lib2).lower().strip()
    if lib1 == lib2:
        return 1.0
    mots1 = set(lib1.split())
    mots2 = set(lib2.split())
    if not mots1 or not mots2:
        return 0
    intersection = mots1 & mots2
    union = mots1 | mots2
    return len(intersection) / len(union) if union else 0


def rapprocher_bancaire(df_releve, df_ecritures, tolerance_jours=3):
    """Effectue un rapprochement bancaire intelligent"""
    df_r = df_releve.copy()
    df_e = df_ecritures.copy()
    
    cols_releve = {col.lower(): col for col in df_r.columns}
    col_date_r = None
    col_lib_r = None
    col_montant_r = None
    col_debit_r = None
    col_credit_r = None
    
    for k in cols_releve:
        if 'date' in k:
            col_date_r = cols_releve[k]
        elif any(x in k for x in ['libelle', 'libellé', 'description', 'operation']):
            col_lib_r = cols_releve[k]
        elif 'montant' in k:
            col_montant_r = cols_releve[k]
        elif 'debit' in k or 'débit' in k:
            col_debit_r = cols_releve[k]
        elif 'credit' in k or 'crédit' in k:
            col_credit_r = cols_releve[k]
    
    cols_ecr = {col.lower(): col for col in df_e.columns}
    col_date_e = None
    col_lib_e = None
    col_debit_e = None
    col_credit_e = None
    
    for k in cols_ecr:
        if 'date' in k:
            col_date_e = cols_ecr[k]
        elif any(x in k for x in ['libelle', 'libellé', 'description', 'lib']):
            col_lib_e = cols_ecr[k]
        elif 'debit' in k or 'débit' in k:
            col_debit_e = cols_ecr[k]
        elif 'credit' in k or 'crédit' in k:
            col_credit_e = cols_ecr[k]
    
    if col_date_r:
        df_r['_date'] = normaliser_date(df_r[col_date_r])
    if col_lib_r:
        df_r['_libelle'] = df_r[col_lib_r].astype(str)
    
    if col_montant_r:
        df_r['_montant'] = normaliser_montant(df_r[col_montant_r])
    elif col_debit_r and col_credit_r:
        df_r['_debit'] = normaliser_montant(df_r[col_debit_r])
        df_r['_credit'] = normaliser_montant(df_r[col_credit_r])
        df_r['_montant'] = df_r['_credit'] - df_r['_debit']
    else:
        df_r['_montant'] = 0
    
    if col_date_e:
        df_e['_date'] = normaliser_date(df_e[col_date_e])
    if col_lib_e:
        df_e['_libelle'] = df_e[col_lib_e].astype(str)
    
    if col_debit_e:
        df_e['_debit'] = normaliser_montant(df_e[col_debit_e])
    else:
        df_e['_debit'] = 0
    
    if col_credit_e:
        df_e['_credit'] = normaliser_montant(df_e[col_credit_e])
    else:
        df_e['_credit'] = 0
    
    df_e['_montant'] = df_e['_debit'] - df_e['_credit']
    
    rapproches = []
    non_rapproches_releve = []
    df_e['_utilise'] = False
    
    for idx_r, row_r in df_r.iterrows():
        montant_r = row_r['_montant']
        date_r = row_r.get('_date')
        lib_r = row_r.get('_libelle', '')
        
        if abs(montant_r) < 0.01:
            continue
        
        meilleur_match = None
        meilleur_score = 0
        
        for idx_e, row_e in df_e[~df_e['_utilise']].iterrows():
            montant_e = row_e['_montant']
            
            if abs(abs(montant_r) - abs(montant_e)) > 0.01:
                continue
            
            score = 0.6
            
            if date_r is not None and pd.notna(date_r) and pd.notna(row_e.get('_date')):
                ecart_jours = abs((date_r - row_e['_date']).days)
                if ecart_jours <= tolerance_jours:
                    score += 0.3 * (1 - ecart_jours/tolerance_jours) if tolerance_jours > 0 else 0.3
            
            if lib_r and row_e.get('_libelle'):
                sim = calculer_similarite_libelle(lib_r, row_e['_libelle'])
                score += 0.1 * sim
            
            if score > meilleur_score:
                meilleur_score = score
                meilleur_match = idx_e
        
        if meilleur_match is not None and meilleur_score >= 0.6:
            df_e.at[meilleur_match, '_utilise'] = True
            rapproches.append({
                'Date relevé': row_r.get('_date'),
                'Libellé relevé': str(lib_r)[:50] if lib_r else '',
                'Montant': montant_r,
                'Date écriture': df_e.at[meilleur_match, '_date'],
                'Score': f"{meilleur_score*100:.0f}%"
            })
        else:
            non_rapproches_releve.append({
                'Date': row_r.get('_date'),
                'Libellé': str(lib_r)[:50] if lib_r else '',
                'Montant': montant_r
            })
    
    non_rapproches_ecritures = []
    for idx_e, row_e in df_e[~df_e['_utilise']].iterrows():
        montant_e = row_e['_montant']
        if abs(montant_e) < 0.01:
            continue
        non_rapproches_ecritures.append({
            'Date': row_e.get('_date'),
            'Libellé': str(row_e.get('_libelle', ''))[:50],
            'Montant': montant_e
        })
    
    return {
        'nb_total_releve': len(df_r),
        'nb_total_ecritures': len(df_e),
        'nb_rapproches': len(rapproches),
        'nb_non_rapproches_releve': len(non_rapproches_releve),
        'nb_non_rapproches_ecritures': len(non_rapproches_ecritures),
        'taux_rapprochement': (len(rapproches) / len(df_r) * 100) if len(df_r) > 0 else 0,
        'rapproches': pd.DataFrame(rapproches) if rapproches else pd.DataFrame(),
        'non_rapproches_releve': pd.DataFrame(non_rapproches_releve) if non_rapproches_releve else pd.DataFrame(),
        'non_rapproches_ecritures': pd.DataFrame(non_rapproches_ecritures) if non_rapproches_ecritures else pd.DataFrame()
    }


def generer_rapport_rapprochement(resultats, nom_compte="Compte bancaire"):
    """Genere un rapport professionnel"""
    rapport = []
    rapport.append(f"# RAPPORT DE RAPPROCHEMENT BANCAIRE")
    rapport.append(f"## {nom_compte}")
    rapport.append(f"*Date : {datetime.now().strftime('%d/%m/%Y')}*")
    rapport.append("")
    rapport.append("---")
    rapport.append("")
    rapport.append("## SYNTHESE")
    rapport.append("")
    rapport.append(f"- Operations releve : {resultats['nb_total_releve']:,}")
    rapport.append(f"- Ecritures comptables : {resultats['nb_total_ecritures']:,}")
    rapport.append(f"- Rapprochees : {resultats['nb_rapproches']:,}")
    rapport.append(f"- Non rapprochees (releve) : {resultats['nb_non_rapproches_releve']:,}")
    rapport.append(f"- Non rapprochees (ecritures) : {resultats['nb_non_rapproches_ecritures']:,}")
    rapport.append(f"- Taux de rapprochement : {resultats['taux_rapprochement']:.1f}%")
    rapport.append("")
    
    if resultats['taux_rapprochement'] >= 90:
        rapport.append("**Excellent** : Rapprochement quasi-complet")
    elif resultats['taux_rapprochement'] >= 70:
        rapport.append("**Bon** : Rapprochement satisfaisant")
    else:
        rapport.append("**A verifier** : Investigations necessaires")
    
    rapport.append("")
    rapport.append("---")
    rapport.append("*SMD Consulting - Superviseur IA Comptable*")
    
    return "\n".join(rapport)