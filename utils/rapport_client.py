# -*- coding: utf-8 -*-
"""Module Rapport Client - SMD Consulting"""
import pandas as pd
from datetime import datetime
from utils.page_helpers import (
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)


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

def page_rapport_client():
    import streamlit as st
    import pandas as pd
    from datetime import datetime
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
    type=["csv", "xlsx", "txt"]
)

df = None
if uploaded_file:
    from utils.intelligent_parser import parser_balance_intelligent

    mode_lecture = st.radio(
        "🔧 Mode de lecture",
        ["🤖 Auto-détection", "📋 Mode manuel"],
        horizontal=True,
        key="rc_mode"
    )

    if mode_lecture == "🤖 Auto-détection":
        try:
            with st.spinner("🤖 Analyse..."):
                if uploaded_file.name.endswith('xlsx') or uploaded_file.name.endswith('csv'):
                    df, info = parser_balance_intelligent(uploaded_file)
                    st.success(f"✅ {info['format_detecte']} | {len(df):,} comptes")
                    if info['colonnes_manquantes']:
                        st.warning(f"⚠ Colonnes non détectées : {', '.join(info['colonnes_manquantes'])}. Essayez le mode manuel.")
                else:
                    df = pd.read_csv(uploaded_file, sep='|', encoding='utf-8')
                    st.success(f"✅ FEC chargé : {len(df):,} lignes")
        except Exception as e:
            st.error(f"Erreur : {e}")

    else:
        col1, col2 = st.columns(2)
        with col1:
            a_un_entete = st.checkbox("✅ Fichier a une ligne d'en-tête", value=True, key="rc_entete")
        with col2:
            ligne_entete = st.number_input("Ligne d'en-tête", min_value=0, max_value=20, value=0, key="rc_ligne") if a_un_entete else None

        try:
            if uploaded_file.name.endswith('xlsx'):
                df = pd.read_excel(uploaded_file, header=ligne_entete if a_un_entete else None)
            else:
                df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8', header=ligne_entete if a_un_entete else None)

            st.success(f"✅ Fichier chargé : {len(df):,} lignes")

            with st.expander("👀 Aperçu"):
                st.dataframe(df.head(15), use_container_width=True)

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

if st.button("📋 Générer le Rapport Client", type="primary", use_container_width=True):
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
                        st.metric("CA", f"{kpis['chiffre_affaires']:,.0f} €")
                    with col2:
                        rn = kpis['resultat_net']
                        st.metric("Résultat Net", f"{rn:,.0f} €",
                                 delta="Bénéfice" if rn > 0 else "Déficit",
                                 delta_color="normal" if rn > 0 else "inverse")
                    with col3:
                        st.metric("EBE", f"{kpis['ebe']:,.0f} €")
                    with col4:
                        st.metric("Trésorerie", f"{kpis['tresorerie']:,.0f} €")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Marge nette", f"{kpis['taux_rentabilite']:.1f}%")
                    with col2:
                        st.metric("Marge brute", f"{kpis['taux_marge_brute']:.1f}%")
                    with col3:
                        st.metric("Taux VA", f"{kpis['taux_va']:.1f}%")
                    with col4:
                        st.metric("Poids personnel", f"{kpis['poids_charges_personnel']:.1f}%")

                    st.divider()

            st.markdown("## 📄 Rapport Généré")
            with st.container():
                afficher_rapport(rapport, afficher_kpis_auto=True, afficher_alertes_auto=True, afficher_tables_auto=True, compact=True)

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Sauvegarder", use_container_width=True):
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

