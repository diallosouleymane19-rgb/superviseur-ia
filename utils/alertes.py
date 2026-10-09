# -*- coding: utf-8 -*-
"""Module Alertes & Anomalies - SMD Global Consulting LLC"""
from utils.sig_pcg import nb_fr
from utils.formats import est_tableur, TYPES_BALANCE, TYPES_TABLEUR_CSV
import pandas as pd
import numpy as np
from datetime import datetime
from utils.page_helpers import (
    bouton_sauvegarde,
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)


def detecter_alertes(df):
    """Détecte automatiquement les anomalies"""
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
            'titre': 'Déséquilibre Débit/Crédit',
            'message': f"Écart de {nb_fr(ecart, 2)} €",
            'count': 1
        })
    
    # 2. Ecritures nulles
    nulles = ((df['_debit'] == 0) & (df['_credit'] == 0)).sum()
    if nulles > 0:
        alertes.append({
            'niveau': 'INFO',
            'titre': 'Écritures montant nul',
            'message': f"{nulles} écritures avec Débit=0 et Crédit=0",
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
                'message': f"{nb_fr(taux_ronds, 1)} % de montants multiples de 100",
                'count': int(montants_ronds)
            })
    
    # 5. Sans libelle
    if 'EcritureLib' in df.columns:
        sans_libelle = df['EcritureLib'].isna().sum()
        if sans_libelle > 0:
            alertes.append({
                'niveau': 'WARNING',
                'titre': 'Écritures sans libellé',
                'message': f"{sans_libelle} écritures sans libellé",
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
                    'titre': 'Écritures week-end',
                    'message': f"{nb_weekend} écritures samedi/dimanche",
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
            'titre': 'Montants négatifs',
            'message': f"{debits_negatifs + credits_negatifs} ligne{'s' if debits_negatifs + credits_negatifs > 1 else ''} avec montant négatif",
            'count': int(debits_negatifs + credits_negatifs)
        })
    
    # 8. Debit ET Credit simultanes
    debit_credit = ((df['_debit'] > 0) & (df['_credit'] > 0)).sum()
    if debit_credit > 0:
        alertes.append({
            'niveau': 'WARNING',
            'titre': 'Débit ET Crédit simultanés',
            'message': f"{debit_credit} écritures avec Débit ET Crédit non nuls",
            'count': int(debit_credit)
        })
    
    # 9. Montants tres eleves
    if len(df) > 0 and 'Debit' in df.columns:
        seuil = df['_debit'].quantile(0.95)
        tres_eleves = (df['_debit'] > seuil * 10).sum()
        if tres_eleves > 0:
            alertes.append({
                'niveau': 'INFO',
                'titre': 'Montants très élevés',
                'message': f"{tres_eleves} écritures > 10x le P95",
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
                'message': f"{comptes_courts} écritures avec compte < 3 caractères",
                'count': int(comptes_courts)
            })
    
    return alertes


def visuels_alertes(alertes):
    """Indicateurs pour l'export Word (mêmes chiffres qu'à l'écran)."""
    n = lambda niv: len([a for a in alertes if a['niveau'] == niv])
    return [{"libelle": "Critiques", "valeur": str(n('CRITIQUE')), "ton": "mauvais" if n('CRITIQUE') else "bon",
             "detail": "investigation urgente" if n('CRITIQUE') else "aucune"},
            {"libelle": "À surveiller", "valeur": str(n('WARNING')), "ton": "mauvais" if n('WARNING') else None,
             "detail": ""},
            {"libelle": "Pour information", "valeur": str(n('INFO')), "detail": ""},
            {"libelle": "Total", "valeur": str(len(alertes)), "detail": ""}], []


def generer_rapport_alertes(alertes, nom_entreprise="Entreprise"):
    """Génère un rapport des alertes"""
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
    
    rapport.append("## SYNTHÈSE")
    rapport.append("")
    rapport.append(f"- Alertes critiques : {nb_critique}")
    rapport.append(f"- Alertes à surveiller : {nb_warning}")
    rapport.append(f"- Alertes info : {nb_info}")
    rapport.append(f"- Total : {len(alertes)}")
    rapport.append("")
    
    if nb_critique > 0:
        rapport.append("**ATTENTION** : Anomalies critiques - Investigation urgente")
    elif nb_warning > 0:
        rapport.append("**Vigilance** : Alertes à investiguer")
    elif len(alertes) == 0:
        rapport.append("**OK** : Aucune anomalie majeure")
    else:
        rapport.append("**Information** : Points à surveiller")
    
    rapport.append("")
    rapport.append("---")
    rapport.append("")
    
    if alertes:
        rapport.append("## DÉTAIL DES ALERTES")
        rapport.append("")
        
        for niveau in ['CRITIQUE', 'WARNING', 'INFO']:
            alertes_n = [a for a in alertes if a['niveau'] == niveau]
            if alertes_n:
                rapport.append(f"### {dict(CRITIQUE='Critiques', WARNING='À surveiller', INFO='Pour information').get(niveau, niveau)}")
                rapport.append("")
                for a in alertes_n:
                    rapport.append(f"- **{a['titre']}** : {a['message']}")
                rapport.append("")
    
    rapport.append("---")
    rapport.append("")
    rapport.append("## RECOMMANDATIONS")
    rapport.append("")
    rapport.append("- Investiguer chaque alerte critique en priorité")
    rapport.append("- Documenter les anomalies dans le dossier de révision")
    rapport.append("- Croiser avec module Loi de Benford pour fraude")
    rapport.append("")
    rapport.append("---")
    rapport.append("*SMD Global Consulting LLC - Superviseur IA Comptable*")
    
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
        type=TYPES_BALANCE
    )

    if uploaded_file:
        from utils.alertes import detecter_alertes, generer_rapport_alertes
        from utils.intelligent_parser import parser_balance_intelligent, charger_balance_ou_fec

        try:
            with st.spinner("🤖 Analyse..."):
                df, _msg, info = charger_balance_ou_fec(uploaded_file)
                st.success(f"✅ {_msg}")
                if info and info.get('colonnes_manquantes'):
                    st.warning(f"⚠ Colonnes non détectées : {', '.join(info['colonnes_manquantes'])}. Vérifiez l'en-tête du fichier.")

            with st.expander("👀 Aperçu"):
                st.dataframe(df.head(10), width="stretch")

            st.divider()

            nom_entreprise = st.text_input("🏢 Nom de l'entreprise", value="Entreprise")

            if st.button("🔍 Détecter les anomalies", type="primary", width="stretch"):
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
                        st.metric("🟡 À surveiller", nb_warning)
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
                        bouton_sauvegarde(type_analyse="Alertes", resultat=rapport, libelle="💾 Sauvegarder")
                    with col2:
                        try:
                            ind_w, graph_w = visuels_alertes(alertes)
                            generer_bouton_word(f"Alertes_{nom_entreprise}", rapport, indicateurs=ind_w,
                                                graphiques=graph_w, sans_sections=("SYNTHÈSE",))
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

