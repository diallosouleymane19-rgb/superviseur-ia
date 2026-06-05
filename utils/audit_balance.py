# -*- coding: utf-8 -*-
"""
Module Audit Balance Professionnel - SMD Global Consulting LLC
Pour Cabinets, DAF et Dirigeants
"""
import pandas as pd
import numpy as np
from datetime import datetime
from utils.page_helpers import (
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)


def detecter_colonnes(df):
    """Detecte automatiquement les colonnes Debit/Credit/Compte"""
    colonnes = {}
    
    # Detection Compte
    for col in df.columns:
        col_lower = str(col).lower()
        if any(x in col_lower for x in ['compte', 'numero', 'comptenum', 'account']):
            colonnes['compte'] = col
            break
    
    # Detection Libelle
    for col in df.columns:
        col_lower = str(col).lower()
        if any(x in col_lower for x in ['libelle', 'intitule', 'designation', 'nom', 'lib']):
            colonnes['libelle'] = col
            break
    
    # Detection Debit
    for col in df.columns:
        col_lower = str(col).lower()
        if 'debit' in col_lower or 'debet' in col_lower:
            colonnes['debit'] = col
            break
    
    # Detection Credit
    for col in df.columns:
        col_lower = str(col).lower()
        if 'credit' in col_lower:
            colonnes['credit'] = col
            break
    
    # Detection Solde
    for col in df.columns:
        col_lower = str(col).lower()
        if 'solde' in col_lower or 'balance' in col_lower:
            colonnes['solde'] = col
            break
    
    return colonnes


def auditer_balance(df):
    """
    Audit complet de la balance comptable
    
    Returns:
        dict: Resultats d'audit avec score et recommandations
    """
    cols = detecter_colonnes(df)
    
    audit = {
        'colonnes_detectees': cols,
        'kpis': {},
        'controles': {},
        'anomalies': [],
        'recommandations': [],
        'score_qualite': 0
    }
    
    # Conversion numerique
    if 'debit' in cols:
        df['_debit'] = pd.to_numeric(df[cols['debit']].astype(str).str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0)
    if 'credit' in cols:
        df['_credit'] = pd.to_numeric(df[cols['credit']].astype(str).str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0)
    
    points = 0
    points_max = 100
    
    # 1. KPIs PRINCIPAUX
    if 'debit' in cols and 'credit' in cols:
        total_debit = df['_debit'].sum()
        total_credit = df['_credit'].sum()
        ecart = abs(total_debit - total_credit)
        
        audit['kpis']['total_debit'] = total_debit
        audit['kpis']['total_credit'] = total_credit
        audit['kpis']['ecart'] = ecart
        audit['kpis']['volume_total'] = total_debit + total_credit
        
        # Controle equilibre
        if ecart < 0.01:
            audit['controles']['Equilibre Debit/Credit'] = {
                'statut': 'OK',
                'message': f'Balance equilibree (ecart = {ecart:.2f} EUR)',
                'gravite': None
            }
            points += 30
        else:
            audit['controles']['Equilibre Debit/Credit'] = {
                'statut': 'KO',
                'message': f'Desequilibre detecte : {ecart:,.2f} EUR',
                'gravite': 'CRITIQUE'
            }
            audit['anomalies'].append({
                'type': 'Desequilibre',
                'gravite': 'CRITIQUE',
                'description': f'Ecart de {ecart:,.2f} EUR entre Debit et Credit'
            })
            audit['recommandations'].append('Verifier l\'integrite des ecritures comptables')
    
    # 2. NOMBRE DE COMPTES
    if 'compte' in cols:
        nb_comptes = df[cols['compte']].nunique()
        audit['kpis']['nb_comptes'] = nb_comptes
        
        if nb_comptes > 0:
            audit['controles']['Nombre de comptes'] = {
                'statut': 'OK',
                'message': f'{nb_comptes} comptes utilises',
                'gravite': None
            }
            points += 15
    
    # 3. ANALYSE PAR CLASSE COMPTABLE (PCG)
    if 'compte' in cols:
        try:
            df['_classe'] = df[cols['compte']].astype(str).str[0]
            classes_pcg = {
                '1': 'Capitaux',
                '2': 'Immobilisations',
                '3': 'Stocks',
                '4': 'Tiers',
                '5': 'Financiers',
                '6': 'Charges',
                '7': 'Produits',
                '8': 'Speciaux'
            }
            
            repartition = df['_classe'].value_counts().to_dict()
            audit['kpis']['repartition_classes'] = {
                classes_pcg.get(k, f'Classe {k}'): v 
                for k, v in repartition.items()
            }
            points += 15
        except:
            pass
    
    # 4. DETECTION COMPTES NON SOLDES (anormaux)
    if 'debit' in cols and 'credit' in cols and 'compte' in cols:
        try:
            df['_solde'] = df['_debit'] - df['_credit']
            
            # Comptes 6 (charges) avec solde crediteur = anormal
            if '_classe' in df.columns:
                charges_creditrices = df[(df['_classe'] == '6') & (df['_solde'] < 0)]
                if len(charges_creditrices) > 0:
                    audit['anomalies'].append({
                        'type': 'Charges creditrices',
                        'gravite': 'MOYENNE',
                        'description': f'{len(charges_creditrices)} comptes de charges (classe 6) avec solde crediteur'
                    })
                
                # Comptes 7 (produits) avec solde debiteur = anormal
                produits_debiteurs = df[(df['_classe'] == '7') & (df['_solde'] > 0)]
                if len(produits_debiteurs) > 0:
                    audit['anomalies'].append({
                        'type': 'Produits debiteurs',
                        'gravite': 'MOYENNE',
                        'description': f'{len(produits_debiteurs)} comptes de produits (classe 7) avec solde debiteur'
                    })
            
            points += 20
        except:
            pass
    
    # 5. RATIOS FINANCIERS
    if 'debit' in cols and 'credit' in cols and '_classe' in df.columns:
        try:
            # Charges totales
            charges = df[df['_classe'] == '6']['_debit'].sum() - df[df['_classe'] == '6']['_credit'].sum()
            # Produits totaux
            produits = df[df['_classe'] == '7']['_credit'].sum() - df[df['_classe'] == '7']['_debit'].sum()
            
            if produits > 0:
                resultat = produits - charges
                marge = (resultat / produits) * 100
                audit['kpis']['charges_totales'] = charges
                audit['kpis']['produits_totaux'] = produits
                audit['kpis']['resultat_estime'] = resultat
                audit['kpis']['marge_pct'] = marge
                
                if marge > 0:
                    audit['controles']['Resultat'] = {
                        'statut': 'OK',
                        'message': f'Resultat positif : {resultat:,.2f} EUR (marge {marge:.1f}%)',
                        'gravite': None
                    }
                else:
                    audit['controles']['Resultat'] = {
                        'statut': 'WARNING',
                        'message': f'Resultat negatif : {resultat:,.2f} EUR',
                        'gravite': 'MOYENNE'
                    }
                points += 20
        except:
            pass
    
    # SCORE FINAL
    audit['score_qualite'] = round((points / points_max) * 100, 1)
    
    # NIVEAU
    if audit['score_qualite'] >= 90:
        audit['niveau'] = 'Excellent'
    elif audit['score_qualite'] >= 75:
        audit['niveau'] = 'Bon'
    elif audit['score_qualite'] >= 50:
        audit['niveau'] = 'A surveiller'
    else:
        audit['niveau'] = 'Critique'
    
    # RECOMMANDATIONS GENERALES
    if not audit['recommandations']:
        if audit['score_qualite'] >= 90:
            audit['recommandations'].append('Balance de qualite excellente - poursuivre les bonnes pratiques')
        else:
            audit['recommandations'].append('Lancer un audit detaille module Loi de Benford')
            audit['recommandations'].append('Verifier la coherence des ecritures via le module FEC')
    
    return audit


def generer_rapport_audit(audit, nom_entreprise="Entreprise"):
    """Genere un rapport d'audit professionnel"""
    
    rapport = []
    rapport.append(f"# RAPPORT D'AUDIT - BALANCE COMPTABLE")
    rapport.append(f"## {nom_entreprise}")
    rapport.append(f"*Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}*\n")
    rapport.append(f"---\n")
    
    # SYNTHESE EXECUTIVE
    rapport.append(f"## 📊 SYNTHESE EXECUTIVE\n")
    rapport.append(f"- **Score qualite** : {audit['score_qualite']}% ({audit['niveau']})")
    rapport.append(f"- **Anomalies detectees** : {len(audit['anomalies'])}")
    rapport.append(f"- **Date d'audit** : {datetime.now().strftime('%d/%m/%Y')}\n")
    
    # KPIs
    if audit['kpis']:
        rapport.append("## 💰 INDICATEURS CLES")
        kpis = audit['kpis']
        if 'total_debit' in kpis:
            rapport.append(f"- **Total Debit** : {kpis['total_debit']:,.2f} EUR")
            rapport.append(f"- **Total Credit** : {kpis['total_credit']:,.2f} EUR")
            rapport.append(f"- **Volume total** : {kpis['volume_total']:,.2f} EUR")
        if 'nb_comptes' in kpis:
            rapport.append(f"- **Nombre de comptes** : {kpis['nb_comptes']}")
        if 'resultat_estime' in kpis:
            rapport.append(f"- **Resultat estime** : {kpis['resultat_estime']:,.2f} EUR")
            rapport.append(f"- **Marge** : {kpis.get('marge_pct', 0):.1f}%")
        rapport.append("")
    
    # CONTROLES
    rapport.append("## 🔍 CONTROLES EFFECTUES")
    for nom, ctrl in audit['controles'].items():
        symbol = '✅' if ctrl['statut'] == 'OK' else '⚠' if ctrl['statut'] == 'WARNING' else '❌'
        rapport.append(f"- {symbol} **{nom}** : {ctrl['message']}")
    rapport.append("")
    
    # ANOMALIES
    if audit['anomalies']:
        rapport.append("## ⚠ ANOMALIES DETECTEES")
        for anomalie in audit['anomalies']:
            rapport.append(f"- **[{anomalie['gravite']}]** {anomalie['type']} : {anomalie['description']}")
        rapport.append("")
    
    # RECOMMANDATIONS
    rapport.append("## 💡 RECOMMANDATIONS")
    for reco in audit['recommandations']:
        rapport.append(f"- {reco}")
    rapport.append("")
    
    rapport.append("---")
    rapport.append("*Rapport genere par SMD Global Consulting LLC - Superviseur IA Comptable*")
    
    return "\n".join(rapport)



def page_audit_balance():
    import streamlit as st
    import pandas as pd
    from datetime import datetime
    from utils.page_helpers import (
        sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
        banniere_demo, is_demo, appel_mistral_securise,
        afficher_rapport, afficher_synthese_score,
    )
    st.title("📊 Audit de Balance Comptable")
    st.markdown("**Analyse approfondie** pour Cabinets, DAF et Dirigeants")
    st.caption("✨ Compatible : Sage, Cegid, EBP, Ciel, ACD, Tiime, Pennylane, QuickBooks")

    uploaded_file = st.file_uploader(
        "📎 Déposer votre balance (CSV, XLSX)", 
        type=["csv", "xlsx"]
    )

    if uploaded_file:
        try:
            from utils.audit_balance import auditer_balance, generer_rapport_audit
            from utils.intelligent_parser import parser_balance_intelligent, nettoyer_balance
        except ImportError as _imp_err:
            st.error(f"Module d'audit indisponible : {_imp_err}")
            st.stop()

        mode_lecture = st.radio(
            "🔧 Mode de lecture",
            ["🤖 Auto-détection universelle", "📋 Mode manuel"],
            horizontal=True
        )

        try:
            if mode_lecture == "🤖 Auto-détection universelle":
                with st.spinner("🤖 Analyse intelligente de la balance..."):
                    df, info = parser_balance_intelligent(uploaded_file)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📊 Format détecté", info['format_detecte'])
                with col2:
                    st.metric("📍 Ligne en-tête", info['ligne_entete'])
                with col3:
                    st.metric("📝 Lignes données", info['nb_lignes_donnees'])

                if info['colonnes_manquantes']:
                    st.warning(f"⚠ Colonnes non détectées : {', '.join(info['colonnes_manquantes'])}. Essayez le mode manuel.")

                with st.expander("🔍 Détails de la détection", expanded=False):
                    st.write("**Mapping des colonnes :**")
                    for orig, std in info['colonnes_mappees'].items():
                        st.write(f"- `{orig}` → **{std}**")

                with st.expander("👀 Aperçu de la balance", expanded=True):
                    st.dataframe(df.head(15), use_container_width=True)

            else:
                col1, col2 = st.columns(2)
                with col1:
                    a_un_entete = st.checkbox("✅ Mon fichier a une ligne d'en-tête", value=True)
                with col2:
                    ligne_entete = st.number_input("Ligne d'en-tête", min_value=0, max_value=20, value=0) if a_un_entete else None

                if uploaded_file.name.endswith('xlsx'):
                    df = pd.read_excel(uploaded_file, header=ligne_entete if a_un_entete else None)
                else:
                    df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8', header=ligne_entete if a_un_entete else None)

                st.success(f"✅ Balance chargée : **{len(df):,} lignes**")

                with st.expander("👀 Aperçu de la balance", expanded=True):
                    st.dataframe(df.head(15), use_container_width=True)

                st.divider()
                st.markdown("### 🎯 Identification des Colonnes")
                colonnes_disponibles = ["-- Aucune --"] + [str(c) for c in df.columns]

                col1, col2 = st.columns(2)
                with col1:
                    col_compte = st.selectbox("🔢 Compte", colonnes_disponibles, index=1 if len(df.columns) > 0 else 0)
                    col_libelle = st.selectbox("📝 Libellé", colonnes_disponibles, index=2 if len(df.columns) > 1 else 0)
                with col2:
                    col_debit = st.selectbox("📥 Débit", colonnes_disponibles, index=3 if len(df.columns) > 2 else 0)
                    col_credit = st.selectbox("📤 Crédit", colonnes_disponibles, index=4 if len(df.columns) > 3 else 0)

                renommage = {}
                if col_compte != "-- Aucune --":
                    renommage[col_compte] = 'CompteNum'
                if col_libelle != "-- Aucune --":
                    renommage[col_libelle] = 'CompteLib'
                if col_debit != "-- Aucune --":
                    renommage[col_debit] = 'Debit'
                if col_credit != "-- Aucune --":
                    renommage[col_credit] = 'Credit'

                df = df.rename(columns=renommage)

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                nom_entreprise = st.text_input("🏢 Nom de l'entreprise", value="Entreprise")
            with col2:
                exercice = st.text_input("📅 Exercice", value=str(datetime.now().year))

            if st.button("🔍 Lancer l'audit professionnel", type="primary", use_container_width=True):
                with st.spinner("Audit en cours..."):
                    audit = auditer_balance(df)

                    afficher_synthese_score(
                        score=audit['score_qualite'],
                        niveau=audit['niveau'],
                        kpis=audit['kpis'],
                        controles=audit['controles'],
                        anomalies=audit['anomalies'],
                        recommandations=audit['recommandations'],
                        devise="€"
                    )

                    st.divider()
                    rapport = generer_rapport_audit(audit, nom_entreprise)
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Sauvegarder", use_container_width=True):
                            sauvegarder_si_autorise(type_analyse="Audit Balance", resultat=rapport)
                            st.success("✅ Sauvegardé !")
                    with col2:
                        try:
                            generer_bouton_word(f"Audit_Balance_{nom_entreprise}", rapport)
                        except Exception as e:
                            st.error(f"Erreur : {e}")

        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")
            import traceback
            with st.expander("Détails techniques"):
                st.code(traceback.format_exc())

    # -----------------------------------------------------------------------------
    # 4. TRAITEMENT FEC - VERSION PROFESSIONNELLE CABINET
    # -----------------------------------------------------------------------------

