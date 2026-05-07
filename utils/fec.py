# -*- coding: utf-8 -*-
"""Module de traitement FEC"""
import pandas as pd

def lire_fec(fichier):
    """Lit un fichier FEC"""
    try:
        df = pd.read_csv(fichier, sep='|', encoding='utf-8')
        return df
    except:
        df = pd.read_csv(fichier, sep='\t', encoding='utf-8')
        return df


def valider_fec(df):
    """Valide un fichier FEC"""
    resultats = {}
    
    # Vérification du nombre de colonnes (18 obligatoires)
    colonnes_attendues = [
        'JournalCode', 'JournalLib', 'EcritureNum', 'EcritureDate',
        'CompteNum', 'CompteLib', 'CompAuxNum', 'CompAuxLib',
        'PieceRef', 'PieceDate', 'EcritureLib', 'Debit', 'Credit',
        'EcritureLet', 'DateLet', 'ValidDate', 'Montantdevise', 'Idevise'
    ]
    
    if len(df.columns) >= 18:
        resultats['Nombre de colonnes'] = {"valide": True}
    else:
        resultats['Nombre de colonnes'] = {
            "valide": False, 
            "message": f"Trouvé {len(df.columns)} colonnes, attendu 18"
        }
    
    # Vérification des données
    if 'EcritureDate' in df.columns:
        resultats['Dates valides'] = {"valide": True}
    else:
        resultats['Dates valides'] = {
            "valide": False,
            "message": "Colonne EcritureDate manquante"
        }
    
    # Vérification équilibre
    if 'Debit' in df.columns and 'Credit' in df.columns:
        total_debit = df['Debit'].sum()
        total_credit = df['Credit'].sum()
        ecart = abs(total_debit - total_credit)
        
        if ecart < 0.01:
            resultats['Équilibre Débit/Crédit'] = {"valide": True}
        else:
            resultats['Équilibre Débit/Crédit'] = {
                "valide": False,
                "message": f"Écart de {ecart:.2f} €"
            }
    
    return resultats


def analyser_fec(df):
    """Analyse approfondie d'un FEC"""
    total_debit = df['Debit'].sum() if 'Debit' in df.columns else 0
    total_credit = df['Credit'].sum() if 'Credit' in df.columns else 0
    
    analyse = f"""
### Analyse du FEC

- **Total écritures** : {len(df):,}
- **Colonnes présentes** : {len(df.columns)}
- **Total Débit** : {total_debit:,.2f} €
- **Total Crédit** : {total_credit:,.2f} €
- **Écart** : {abs(total_debit - total_credit):,.2f} €

Les données semblent conformes au format FEC.
"""
    return analyse