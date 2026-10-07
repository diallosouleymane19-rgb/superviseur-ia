# -*- coding: utf-8 -*-
"""Module Rapport Client - SMD Global Consulting LLC"""
from utils.formats import est_tableur, TYPES_BALANCE, TYPES_TABLEUR_CSV
import pandas as pd
from datetime import datetime
from utils.page_helpers import (
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)


def _nb(x, dec=0):
    """Nombre au format français : 61 497 ou 82,8"""
    x = round(float(x), dec) + 0.0  # évite l'affichage « -0 »
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")


def _eur(x):
    """Montant en euros au format français : 61 497 €"""
    return _nb(x) + " €"


def _pct(x):
    """Pourcentage au format français : 82,8 %"""
    return _nb(x, 1) + " %"


def analyser_donnees_client(df):
    """KPIs du client : SIG et postes du bilan selon le PCG (voir utils/sig_pcg.py)."""
    if 'CompteNum' not in df.columns:
        return {'erreur': 'Colonne CompteNum manquante', 'chiffre_affaires': 0}
    from utils.sig_pcg import calculer_sig
    return calculer_sig(df)


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
        rapport.append(f"- **Chiffre d'affaires** : {_eur(ca)}")
        rapport.append(f"- **Résultat net** : {_eur(rn)} ({_pct(kpis['taux_rentabilite'])} du CA)")
        rapport.append(f"- **EBE** : {_eur(ebe)} ({_pct(kpis['taux_ebe'])} du CA)")
        rapport.append(f"- **Valeur ajoutée** : {_eur(kpis['valeur_ajoutee'])} ({_pct(kpis['taux_va'])} du CA)")
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
        rapport.append("### Soldes intermédiaires de gestion")
        rapport.append("")
        rapport.append("| Indicateur | Montant (€) | % du CA |")
        rapport.append("|------------|---------------|---------|")
        ca = kpis['chiffre_affaires']
        rapport.append(f"| Chiffre d'affaires | {_nb(ca)} | 100 % |")
        if kpis['ventes_marchandises'] > 0:
            rapport.append(f"| Marge commerciale | {_nb(kpis['marge_commerciale'])} | {_pct(kpis['taux_marge_commerciale'])} des ventes de marchandises |")
        rapport.append(f"| Production de l'exercice | {_nb(kpis['production_exercice'])} | {_pct(kpis['production_exercice']/ca*100)} |")
        rapport.append(f"| Valeur ajoutée | {_nb(kpis['valeur_ajoutee'])} | {_pct(kpis['taux_va'])} |")
        rapport.append(f"| Excédent brut d'exploitation | {_nb(kpis['ebe'])} | {_pct(kpis['taux_ebe'])} |")
        rapport.append(f"| Résultat d'exploitation | {_nb(kpis['resultat_exploitation'])} | {_pct(kpis['resultat_exploitation']/ca*100)} |")
        rapport.append(f"| Résultat financier | {_nb(kpis['resultat_financier'])} | {_pct(kpis['resultat_financier']/ca*100)} |")
        rapport.append(f"| Résultat exceptionnel | {_nb(kpis['resultat_exceptionnel'])} | {_pct(kpis['resultat_exceptionnel']/ca*100)} |")
        rapport.append(f"| Résultat net | {_nb(kpis['resultat_net'])} | {_pct(kpis['taux_rentabilite'])} |")
        rapport.append(f"| Charges de personnel | {_nb(kpis['masse_salariale'])} | {_pct(kpis['poids_charges_personnel'])} |")
        if abs(kpis.get('ecart_controle', 0)) >= 0.01:
            rapport.append("")
            rapport.append(f"⚠ Contrôle : écart de {_eur(kpis['ecart_controle'])} entre le résultat par les SIG et classe 7 - classe 6. Vérifier le plan de comptes.")
        rapport.append("")
        
        rapport.append("### Bilan")
        rapport.append("")
        rapport.append("| Poste | Montant (€) |")
        rapport.append("|-------|---------------|")
        rapport.append(f"| Immobilisations nettes | {_nb(kpis['immobilisations'])} |")
        rapport.append(f"| Stocks nets | {_nb(kpis['stocks'])} |")
        rapport.append(f"| Créances clients nettes | {_nb(kpis['creances_clients'])} |")
        rapport.append(f"| Trésorerie nette | {_nb(kpis['tresorerie'])} |")
        rapport.append(f"| Capital social | {_nb(kpis['capital'])} |")
        rapport.append(f"| Capitaux propres (résultat inclus) | {_nb(kpis['capitaux_propres'])} |")
        rapport.append(f"| Dettes financières | {_nb(kpis['dettes_financieres'])} |")
        rapport.append(f"| Dettes fournisseurs | {_nb(kpis['dettes_fournisseurs'])} |")
        rapport.append("")
        rapport.append("---")
        rapport.append("")
    
    rapport.append("## ANALYSE DU CABINET")
    rapport.append("")
    
    if kpis and kpis.get('chiffre_affaires', 0) > 0:
        if kpis['taux_rentabilite'] > 10:
            rapport.append("- **Rentabilite excellente** : marge nette > 10 %")
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
            rapport.append("- **Charges personnel elevees** (>50 % CA) : optimiser productivite")
        
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
    rapport.append("*Rapport genere par SMD Global Consulting LLC - Superviseur IA Comptable*")
    rapport.append(f"*(c) {datetime.now().year} - Tous droits reserves*")
    
    return "\n".join(rapport)



def page_rapport_client():
    import streamlit as st
    import pandas as pd
    from datetime import datetime
    from utils.page_helpers import (
        sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
        banniere_demo, is_demo, appel_mistral_securise,
        afficher_rapport, afficher_synthese_score,
    )
    st.title("📋 Rapport Client")
    st.markdown("**Livrable professionnel** pour vos clients")
    st.caption("✨ Synthèse + KPIs + Analyse + Recommandations")

    st.markdown("### 👤 Informations Client")

    col1, col2 = st.columns(2)
    with col1:
        nom_client = st.text_input("🏢 Nom du client", placeholder="Ex: SARL DARLING")
        siret = st.text_input("🆔 SIRET")
        secteur = st.text_input("🏭 Secteur d'activité")

    with col2:
        periode = st.selectbox("📆 Période", ["Mensuel", "Trimestriel", "Semestriel", "Annuel"])
        exercice = st.number_input("📅 Exercice", min_value=2020, max_value=2030, value=2026)
        date_rapport = st.date_input("📋 Date du rapport")

    st.divider()

    st.markdown("### 📂 Données Comptables")

    uploaded_file = st.file_uploader(
        "📎 Balance ou FEC du client",
        type=TYPES_BALANCE
    )

    df = None
    if uploaded_file:
        from utils.intelligent_parser import parser_balance_intelligent, charger_balance_ou_fec

        mode_lecture = st.radio(
            "🔧 Mode de lecture",
            ["🤖 Auto-détection", "📋 Mode manuel"],
            horizontal=True,
            key="rc_mode"
        )

        if mode_lecture == "🤖 Auto-détection":
            try:
                with st.spinner("🤖 Analyse..."):
                    df, _msg, info = charger_balance_ou_fec(uploaded_file)
                    st.success(f"✅ {_msg}")
                    if info and info.get('colonnes_manquantes'):
                        st.warning(f"⚠ Colonnes non détectées : {', '.join(info['colonnes_manquantes'])}. Vérifiez l'en-tête du fichier.")
            except Exception as e:
                st.error(f"Erreur : {e}")

        else:
            col1, col2 = st.columns(2)
            with col1:
                a_un_entete = st.checkbox("✅ Fichier a une ligne d'en-tête", value=True, key="rc_entete")
            with col2:
                ligne_entete = st.number_input("Ligne d'en-tête", min_value=0, max_value=20, value=0, key="rc_ligne") if a_un_entete else None

            try:
                if est_tableur(uploaded_file.name):
                    df = pd.read_excel(uploaded_file, header=ligne_entete if a_un_entete else None)
                else:
                    df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8', header=ligne_entete if a_un_entete else None)

                st.success(f"✅ Fichier chargé : {_nb(len(df))} lignes")

                with st.expander("👀 Aperçu"):
                    st.dataframe(df.head(15), width="stretch")

                st.markdown("#### 🎯 Mapping des colonnes")
                colonnes_disponibles = ["-- Aucune --"] + [str(c) for c in df.columns]

                col1, col2 = st.columns(2)
                with col1:
                    col_compte = st.selectbox("🔢 Compte", colonnes_disponibles, index=1 if len(df.columns) > 0 else 0, key="rc_cc")
                    col_debit = st.selectbox("📥 Débit", colonnes_disponibles, index=3 if len(df.columns) > 2 else 0, key="rc_cd")
                with col2:
                    col_libelle = st.selectbox("📝 Libellé", colonnes_disponibles, index=2 if len(df.columns) > 1 else 0, key="rc_cl")
                    col_credit = st.selectbox("📤 Crédit", colonnes_disponibles, index=4 if len(df.columns) > 3 else 0, key="rc_cre")

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

            except Exception as e:
                st.error(f"Erreur : {e}")

    st.divider()

    st.markdown("### ✍ Personnalisation")

    col1, col2 = st.columns(2)
    with col1:
        observations = st.text_area(
            "📝 Observations particulières",
            placeholder="Évènements marquants, points d'attention...",
            height=120
        )
    with col2:
        objectifs = st.text_area(
            "🎯 Objectifs prochaine période",
            placeholder="Objectifs de croissance, plans d'action...",
            height=120
        )

    st.divider()

    if st.button("📋 Générer le Rapport Client", type="primary", width="stretch"):
        if not nom_client:
            st.error("⚠ Veuillez renseigner le nom du client")
        else:
            from utils.rapport_client import generer_rapport_client, analyser_donnees_client

            df_analyse = df if df is not None else pd.DataFrame()

            with st.spinner("Génération du rapport..."):
                rapport = generer_rapport_client(
                    nom_client=nom_client,
                    siret=siret,
                    periode=periode,
                    exercice=exercice,
                    donnees=df_analyse,
                    observations=observations,
                    objectifs=objectifs
                )

                if df is not None and 'CompteNum' in df.columns:
                    kpis = analyser_donnees_client(df)

                    if kpis.get('chiffre_affaires', 0) > 0:
                        st.markdown("## 📊 Aperçu KPIs Client")

                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("CA", f"{_eur(kpis['chiffre_affaires'])}")
                        with col2:
                            rn = kpis['resultat_net']
                            st.metric("Résultat Net", f"{_eur(rn)}",
                                     delta="Bénéfice" if rn > 0 else "Déficit",
                                     delta_color="normal" if rn > 0 else "inverse")
                        with col3:
                            st.metric("EBE", f"{_eur(kpis['ebe'])}")
                        with col4:
                            st.metric("Trésorerie nette", f"{_eur(kpis['tresorerie'])}")

                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Marge nette", f"{_pct(kpis['taux_rentabilite'])}")
                        with col2:
                            st.metric("Taux d'EBE", f"{_pct(kpis['taux_ebe'])}")
                        with col3:
                            st.metric("Taux de VA", f"{_pct(kpis['taux_va'])}")
                        with col4:
                            st.metric("Charges de personnel / CA", f"{_pct(kpis['poids_charges_personnel'])}")

                        st.divider()

                st.markdown("## 📄 Rapport Généré")
                with st.container():
                    afficher_rapport(rapport, afficher_kpis_auto=True, afficher_alertes_auto=True, afficher_tables_auto=True, compact=True)

                st.divider()

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Sauvegarder", width="stretch"):
                        sauvegarder_si_autorise(type_analyse="Rapport Client", resultat=rapport)
                        st.success("✅ Sauvegardé !")

                with col2:
                    try:
                        nom_fichier = f"Rapport_{nom_client.replace(' ', '_')}_{periode}_{exercice}"
                        generer_bouton_word(nom_fichier, rapport)
                    except Exception as e:
                        st.error(f"Erreur : {e}")

    # -----------------------------------------------------------------------------
    # 10. ALERTES & ANOMALIES - VERSION PROFESSIONNELLE
    # -----------------------------------------------------------------------------

