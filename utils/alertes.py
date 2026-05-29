# -*- coding: utf-8 -*-
"""Module Alertes & Anomalies - SMD Consulting"""
import pandas as pd
import numpy as np
from datetime import datetime
from utils.page_helpers import (
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)


def detecter_alertes(df):
    """Detecte automatiquement les anomalies"""
    alertes = []
    
    df = df.copy()
    if 'Debit' in df.columns:
        df['_debit'] = pd.to_numeric(df['Debit'].astype(str).str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0)
    else:
        df['_debit'] = 0
    
    if 'Credit' in df.columns:
        df['_credit'] = pd.to_numeric(df['Credit'].astype(str).str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0)
    else:
        df['_credit'] = 0
    
    # 1. Equilibre
    total_debit = df['_debit'].sum()
    total_credit = df['_credit'].sum()
    ecart = abs(total_debit - total_credit)
    
    if ecart > 0.01:
        alertes.append({
            'niveau': 'CRITIQUE',
            'titre': 'Desequilibre Debit/Credit',
            'message': f"Ecart de {ecart:,.2f} EUR",
            'count': 1
        })
    
    # 2. Ecritures nulles
    nulles = ((df['_debit'] == 0) & (df['_credit'] == 0)).sum()
    if nulles > 0:
        alertes.append({
            'niveau': 'INFO',
            'titre': 'Ecritures montant nul',
            'message': f"{nulles} ecritures avec Debit=0 et Credit=0",
            'count': int(nulles)
        })
    
    # 3. Doublons
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        alertes.append({
            'niveau': 'WARNING',
            'titre': 'Doublons exacts',
            'message': f"{duplicates} lignes en doublons exacts",
            'count': int(duplicates)
        })
    
    # 4. Montants ronds
    montants = pd.concat([df[df['_debit'] > 0]['_debit'], df[df['_credit'] > 0]['_credit']])
    if len(montants) > 0:
        montants_ronds = (montants % 100 == 0).sum()
        taux_ronds = (montants_ronds / len(montants) * 100)
        
        if taux_ronds > 30:
            alertes.append({
                'niveau': 'WARNING',
                'titre': 'Montants ronds suspects',
                'message': f"{taux_ronds:.1f}% de montants multiples de 100",
                'count': int(montants_ronds)
            })
    
    # 5. Sans libelle
    if 'EcritureLib' in df.columns:
        sans_libelle = df['EcritureLib'].isna().sum()
        if sans_libelle > 0:
            alertes.append({
                'niveau': 'WARNING',
                'titre': 'Ecritures sans libelle',
                'message': f"{sans_libelle} ecritures sans libelle",
                'count': int(sans_libelle)
            })
    
    # 6. Week-end
    if 'EcritureDate' in df.columns:
        try:
            dates = pd.to_datetime(df['EcritureDate'], format='%Y%m%d', errors='coerce')
            weekend = dates.dt.weekday >= 5
            nb_weekend = weekend.sum()
            if nb_weekend > 0:
                alertes.append({
                    'niveau': 'INFO',
                    'titre': 'Ecritures week-end',
                    'message': f"{nb_weekend} ecritures samedi/dimanche",
                    'count': int(nb_weekend)
                })
        except:
            pass
    
    # 7. Montants negatifs
    debits_negatifs = (df['_debit'] < 0).sum()
    credits_negatifs = (df['_credit'] < 0).sum()
    if debits_negatifs > 0 or credits_negatifs > 0:
        alertes.append({
            'niveau': 'WARNING',
            'titre': 'Montants negatifs',
            'message': f"{debits_negatifs + credits_negatifs} ecritures avec montants negatifs",
            'count': int(debits_negatifs + credits_negatifs)
        })
    
    # 8. Debit ET Credit simultanes
    debit_credit = ((df['_debit'] > 0) & (df['_credit'] > 0)).sum()
    if debit_credit > 0:
        alertes.append({
            'niveau': 'WARNING',
            'titre': 'Debit ET Credit simultanes',
            'message': f"{debit_credit} ecritures avec Debit ET Credit non nuls",
            'count': int(debit_credit)
        })
    
    # 9. Montants tres eleves
    if len(df) > 0 and 'Debit' in df.columns:
        seuil = df['_debit'].quantile(0.95)
        tres_eleves = (df['_debit'] > seuil * 10).sum()
        if tres_eleves > 0:
            alertes.append({
                'niveau': 'INFO',
                'titre': 'Montants tres eleves',
                'message': f"{tres_eleves} ecritures > 10x le P95",
                'count': int(tres_eleves)
            })
    
    # 10. Comptes invalides
    if 'CompteNum' in df.columns:
        compte_str = df['CompteNum'].astype(str).str.strip()
        comptes_courts = (compte_str.str.len() < 3).sum()
        if comptes_courts > 0:
            alertes.append({
                'niveau': 'WARNING',
                'titre': 'Comptes invalides',
                'message': f"{comptes_courts} ecritures avec compte < 3 caracteres",
                'count': int(comptes_courts)
            })
    
    return alertes


def generer_rapport_alertes(alertes, nom_entreprise="Entreprise"):
    """Genere un rapport des alertes"""
    rapport = []
    rapport.append(f"# RAPPORT D'ALERTES ET ANOMALIES")
    rapport.append(f"## {nom_entreprise}")
    rapport.append(f"*Date : {datetime.now().strftime('%d/%m/%Y')}*")
    rapport.append("")
    rapport.append("---")
    rapport.append("")
    
    nb_critique = len([a for a in alertes if a['niveau'] == 'CRITIQUE'])
    nb_warning = len([a for a in alertes if a['niveau'] == 'WARNING'])
    nb_info = len([a for a in alertes if a['niveau'] == 'INFO'])
    
    rapport.append("## SYNTHESE")
    rapport.append("")
    rapport.append(f"- Alertes critiques : {nb_critique}")
    rapport.append(f"- Alertes warnings : {nb_warning}")
    rapport.append(f"- Alertes info : {nb_info}")
    rapport.append(f"- Total : {len(alertes)}")
    rapport.append("")
    
    if nb_critique > 0:
        rapport.append("**ATTENTION** : Anomalies critiques - Investigation urgente")
    elif nb_warning > 0:
        rapport.append("**Vigilance** : Alertes a investiguer")
    elif len(alertes) == 0:
        rapport.append("**OK** : Aucune anomalie majeure")
    else:
        rapport.append("**Information** : Points a surveiller")
    
    rapport.append("")
    rapport.append("---")
    rapport.append("")
    
    if alertes:
        rapport.append("## DETAIL DES ALERTES")
        rapport.append("")
        
        for niveau in ['CRITIQUE', 'WARNING', 'INFO']:
            alertes_n = [a for a in alertes if a['niveau'] == niveau]
            if alertes_n:
                rapport.append(f"### {niveau}")
                rapport.append("")
                for a in alertes_n:
                    rapport.append(f"- **{a['titre']}** : {a['message']}")
                rapport.append("")
    
    rapport.append("---")
    rapport.append("")
    rapport.append("## RECOMMANDATIONS")
    rapport.append("")
    rapport.append("- Investiguer chaque alerte critique en priorite")
    rapport.append("- Documenter les anomalies dans le dossier de revision")
    rapport.append("- Croiser avec module Loi de Benford pour fraude")
    rapport.append("")
    rapport.append("---")
    rapport.append("*SMD Consulting - Superviseur IA Comptable*")
    
    return "\n".join(rapport)



def page_alertes():
    import streamlit as st
    import pandas as pd
    from datetime import datetime
    from utils.page_helpers import (
        sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
        banniere_demo, is_demo, appel_mistral_securise,
        afficher_rapport, afficher_synthese_score,
    )
    st.title("⚠ Alertes & Anomalies")
    st.markdown("**Détection automatique** d'anomalies multi-niveaux")
    st.caption("✨ 10 contrôles automatiques pour cabinets et DAF")

    with st.expander("ℹ Quels contrôles sont effectués ?"):
        st.markdown("""
        Le module détecte automatiquement :

        🔴 **CRITIQUE**
        - Déséquilibre Débit/Crédit

        🟡 **WARNING**
        - Doublons exacts
        - Montants ronds suspects (>30%)
        - Écritures sans libellé
        - Montants négatifs
        - Débit ET Crédit simultanés
        - Numéros de comptes invalides

        🔵 **INFO**
        - Écritures montant nul
        - Montants très répétés
        - Écritures week-end
        - Montants très élevés (>10x P95)
        - Charges créditrices
        """)

    uploaded_file = st.file_uploader(
        "📎 Données comptables (FEC, Balance, CSV, XLSX)",
        type=["csv", "xlsx", "txt"]
    )

    if uploaded_file:
        from utils.alertes import detecter_alertes, generer_rapport_alertes
        from utils.intelligent_parser import parser_balance_intelligent

        try:
            with st.spinner("🤖 Analyse..."):
                if uploaded_file.name.endswith('xlsx') or uploaded_file.name.endswith('csv'):
                    try:
                        df, info = parser_balance_intelligent(uploaded_file)
                        st.success(f"✅ Format détecté : **{info['format_detecte']}** | **{len(df):,} lignes**")
                    except:
                        if uploaded_file.name.endswith('xlsx'):
                            df = pd.read_excel(uploaded_file)
                        else:
                            df = pd.read_csv(uploaded_file, sep=None, engine='python')
                        st.success(f"✅ Fichier chargé : **{len(df):,} lignes**")
                else:
                    df = pd.read_csv(uploaded_file, sep='|', encoding='utf-8')
                    st.success(f"✅ FEC chargé : **{len(df):,} lignes**")

            with st.expander("👀 Aperçu"):
                st.dataframe(df.head(10), use_container_width=True)

            st.divider()

            nom_entreprise = st.text_input("🏢 Nom de l'entreprise", value="Entreprise")

            if st.button("🔍 Détecter les anomalies", type="primary", use_container_width=True):
                with st.spinner("Analyse en cours..."):
                    alertes = detecter_alertes(df)

                    nb_critique = len([a for a in alertes if a['niveau'] == 'CRITIQUE'])
                    nb_warning = len([a for a in alertes if a['niveau'] == 'WARNING'])
                    nb_info = len([a for a in alertes if a['niveau'] == 'INFO'])

                    st.markdown("## 📊 Résumé des Alertes")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("🔴 Critiques", nb_critique,
                                 delta_color="inverse" if nb_critique > 0 else "normal")
                    with col2:
                        st.metric("🟡 Warnings", nb_warning)
                    with col3:
                        st.metric("🔵 Infos", nb_info)
                    with col4:
                        st.metric("📊 Total", len(alertes))

                    if nb_critique > 0:
                        st.error("🚨 **ATTENTION** : Anomalies critiques détectées - Investigation urgente !")
                    elif nb_warning > 0:
                        st.warning("⚠ **Vigilance** : Alertes à investiguer")
                    elif len(alertes) == 0:
                        st.success("✅ **Aucune anomalie majeure détectée** - Données saines")
                    else:
                        st.info("ℹ **Points à surveiller** identifiés")

                    st.divider()

                    if alertes:
                        alertes_critiques = [a for a in alertes if a['niveau'] == 'CRITIQUE']
                        if alertes_critiques:
                            st.markdown("### 🔴 Alertes CRITIQUES")
                            for a in alertes_critiques:
                                st.error(f"**{a['titre']}** ({a['count']}) : {a['message']}")

                        alertes_warning = [a for a in alertes if a['niveau'] == 'WARNING']
                        if alertes_warning:
                            st.markdown("### 🟡 Alertes WARNING")
                            for a in alertes_warning:
                                st.warning(f"**{a['titre']}** ({a['count']}) : {a['message']}")

                        alertes_info = [a for a in alertes if a['niveau'] == 'INFO']
                        if alertes_info:
                            st.markdown("### 🔵 Alertes INFO")
                            for a in alertes_info:
                                st.info(f"**{a['titre']}** ({a['count']}) : {a['message']}")

                    st.divider()

                    rapport = generer_rapport_alertes(alertes, nom_entreprise)

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Sauvegarder", use_container_width=True):
                            sauvegarder_si_autorise(type_analyse="Alertes", resultat=rapport)
                            st.success("✅ Sauvegardé !")
                    with col2:
                        try:
                            generer_bouton_word(f"Alertes_{nom_entreprise}", rapport)
                        except Exception as e:
                            st.error(f"Erreur : {e}")

        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")
            import traceback
            with st.expander("Détails techniques"):
                st.code(traceback.format_exc())

    # -----------------------------------------------------------------------------
    # 11. COHÉRENCE DES DONNÉES - VERSION PROFESSIONNELLE
    # -----------------------------------------------------------------------------

