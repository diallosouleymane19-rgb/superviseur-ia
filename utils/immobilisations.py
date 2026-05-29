# -*- coding: utf-8 -*-
"""
Module Immobilisations - SMD Consulting
Gestion des amortissements, cessions et plan d'investissement
"""
import pandas as pd
import numpy as np
from datetime import datetime


import pandas as pd
from datetime import datetime
from utils.page_helpers import (
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)

def calculer_amortissement_lineaire(valeur_origine, duree_ans, date_acquisition):
    """Calcule le tableau d'amortissement linéaire au prorata mensuel"""
    taux = 100 / duree_ans
    
    # 1. Calcul du prorata de la première année (mois d'achat inclus)
    mois_restants = 12 - date_acquisition.month + 1
    annuite_an1 = (valeur_origine * (taux / 100)) * (mois_restants / 12)
    
    # 2. Préparation du tableau
    annees = []
    lignes = []
    vnc = valeur_origine
    amort_cumule = 0
    
    for i in range(duree_ans + 1):
        annee = date_acquisition.year + i
        if i == 0:
            dotation = annuite_an1
        elif i == duree_ans:
            # Solde de la dernière année (ce qui reste pour arriver à 0)
            dotation = valeur_origine - amort_cumule
        else:
            dotation = valeur_origine * (taux / 100)
            
        # Arrondir la dotation pour éviter les problèmes de virgules flottantes
        dotation = round(min(dotation, valeur_origine - amort_cumule), 2)
        
        if dotation <= 0: break
        
        amort_cumule += dotation
        vnc -= dotation
        
        lignes.append({
            "Année": annee,
            "Valeur Origine (€)": valeur_origine,
            "Taux (%)": round(taux, 2),
            "Dotation (€)": dotation,
            "Amort. Cumulé (€)": round(amort_cumule, 2),
            "VNC (€)": round(max(vnc, 0), 2),
            "Statut": "Passé" if annee < datetime.now().year else "En cours" if annee == datetime.now().year else "À venir"
        })
        
    return pd.DataFrame(lignes)

def calculer_amortissement_degressif(valeur_origine, duree_ans, date_acquisition, date_calcul=None):
    """Calcule le tableau d'amortissement dégressif"""
    if date_calcul is None:
        date_calcul = datetime.now()
    
    # Coefficients fiscaux français
    coefficients = {3: 1.25, 4: 1.25, 5: 1.75, 6: 1.75, 7: 2.25, 10: 2.25}
    coeff = 2.25
    for duree_seuil, c in sorted(coefficients.items()):
        if duree_ans <= duree_seuil:
            coeff = c
            break
    
    taux_degressif = (100 / duree_ans) * coeff
    
    tableau = []
    vnc_debut = valeur_origine
    cumul = 0
    
    for annee in range(1, duree_ans + 1):
        annees_restantes = duree_ans - annee + 1
        taux_lineaire_restant = 100 / annees_restantes
        
        # Bascule vers linéaire si plus avantageux
        if taux_lineaire_restant > taux_degressif:
            dotation = vnc_debut / annees_restantes
        else:
            dotation = vnc_debut * taux_degressif / 100
        
        # Prorata première année
        if annee == 1:
            jours_restants = (datetime(date_acquisition.year + 1, 1, 1) - date_acquisition).days
            dotation = dotation * jours_restants / 365
        
        cumul += dotation
        vnc_fin = max(vnc_debut - dotation, 0)
        
        statut = "✅ Passé"
        if date_calcul.year == date_acquisition.year + annee - 1:
            statut = "📍 En cours"
        elif date_calcul.year < date_acquisition.year + annee - 1:
            statut = "🔮 Futur"
        
        tableau.append({
            'Année': date_acquisition.year + annee - 1,
            'VNC Début (€)': round(vnc_debut, 2),
            'Taux Dégressif (%)': round(taux_degressif, 2),
            'Dotation (€)': round(dotation, 2),
            'Amort. Cumulé (€)': round(cumul, 2),
            'VNC Fin (€)': round(vnc_fin, 2),
            'Statut': statut
        })
        
        vnc_debut = vnc_fin
    
    return pd.DataFrame(tableau)


def calculer_cession(valeur_origine, amort_cumule, prix_cession, date_cession, taux_is=25):
    """Calcule la plus ou moins-value de cession"""
    vnc = valeur_origine - amort_cumule
    resultat_cession = prix_cession - vnc
    
    type_resultat = "Plus-value" if resultat_cession > 0 else "Moins-value"
    impot_estime = max(resultat_cession * taux_is / 100, 0) if resultat_cession > 0 else 0
    
    # Écritures comptables
    ecritures = []
    
    # Sortie du bien
    ecritures.append({
        'Compte': '28xx',
        'Libellé': 'Amortissements cumulés',
        'Débit': round(amort_cumule, 2),
        'Crédit': 0
    })
    ecritures.append({
        'Compte': '512',
        'Libellé': 'Banque (prix de cession)',
        'Débit': round(prix_cession, 2),
        'Crédit': 0
    })
    
    if resultat_cession >= 0:
        ecritures.append({
            'Compte': '2xxx',
            'Libellé': 'Immobilisation (valeur origine)',
            'Débit': 0,
            'Crédit': round(valeur_origine, 2)
        })
        ecritures.append({
            'Compte': '775',
            'Libellé': 'Produit de cession',
            'Débit': 0,
            'Crédit': round(prix_cession, 2)
        })
    else:
        ecritures.append({
            'Compte': '675',
            'Libellé': 'Valeur nette comptable cédée',
            'Débit': round(vnc, 2),
            'Crédit': 0
        })
        ecritures.append({
            'Compte': '2xxx',
            'Libellé': 'Immobilisation (valeur origine)',
            'Débit': 0,
            'Crédit': round(valeur_origine, 2)
        })
    
    return {
        'valeur_origine': valeur_origine,
        'amort_cumule': amort_cumule,
        'vnc': round(vnc, 2),
        'prix_cession': prix_cession,
        'resultat_cession': round(resultat_cession, 2),
        'type_resultat': type_resultat,
        'impot_estime': round(impot_estime, 2),
        'ecritures': pd.DataFrame(ecritures)
    }


def generer_rapport_immobilisation(bien, tableau, mode):
    """Génère un rapport professionnel"""
    rapport = [f"# TABLEAU D'AMORTISSEMENT — {bien}"]
    rapport.append(f"Mode : {mode}")
    rapport.append(f"*Généré le {datetime.now().strftime('%d/%m/%Y')}*\n---\n")
    
    for _, row in tableau.iterrows():
        rapport.append(
            f"- {int(row['Année'])} : Dotation {row.get('Dotation (€)', 0):,.2f} € | "
            f"VNC {row.get('VNC (€)', row.get('VNC Fin (€)', 0)):,.2f} € | {row['Statut']}"
        )
    
    rapport.append("\n---")
    rapport.append("*SMD Consulting - Superviseur IA Comptable*")
    return "\n".join(rapport)
def generer_ecritures_amortissement(nom_bien, tableau, exercice_courant=None):
    """Génère les écritures comptables d'amortissement"""
    if exercice_courant is None:
        exercice_courant = datetime.now().year
    
    ecritures = []
    
    for _, row in tableau.iterrows():
        annee = int(row['Année'])
        dotation = row['Dotation (€)']
        
        if dotation > 0:
            ecritures.append({
                'Année': annee,
                'Date': f"31/12/{annee}",
                'Compte Débit': '6811',
                'Libellé Débit': f"Dotation amort. — {nom_bien}",
                'Débit (€)': round(dotation, 2),
                'Compte Crédit': '28xx',
                'Libellé Crédit': f"Amort. {nom_bien}",
                'Crédit (€)': round(dotation, 2),
                'Statut': row['Statut']
            })
    
    return pd.DataFrame(ecritures)


def page_immobilisations():
    import streamlit as st
    import pandas as pd
    from datetime import datetime
st.title("📦 Gestion des Immobilisations")
st.markdown("**Amortissements, Cessions et Plan d'investissement**")
st.caption("✨ Linéaire, Dégressif, Plus/Moins-value de cession")

from utils.immobilisations import (
    calculer_amortissement_lineaire,
    calculer_amortissement_degressif,
    calculer_cession,
    generer_rapport_immobilisation
)

onglet1, onglet2, onglet3 = st.tabs([
    "📋 Tableau d'amortissement",
    "🔄 Cession / Sortie",
    "📊 Plan d'investissement"
])

# ── ONGLET 1 : TABLEAU D'AMORTISSEMENT ──
with onglet1:
    st.markdown("### 📋 Tableau d'amortissement")

    col1, col2 = st.columns(2)
    with col1:
        nom_bien = st.text_input("🏷 Désignation du bien", placeholder="Ex: Véhicule utilitaire")
        valeur_origine = st.number_input("💰 Valeur d'origine (€)", min_value=0.0, value=10000.0, step=100.0)
        duree_ans = st.number_input("⏱ Durée d'amortissement (ans)", min_value=1, max_value=50, value=5)
    with col2:
        date_acquisition = st.date_input("📅 Date d'acquisition")
        mode = st.selectbox("⚙ Mode d'amortissement", ["Linéaire", "Dégressif"])
        categorie = st.selectbox("🏭 Catégorie", [
            "Matériel et outillage (5 ans)",
            "Véhicules (4-5 ans)",
            "Mobilier (10 ans)",
            "Matériel informatique (3 ans)",
            "Constructions (20-50 ans)",
            "Agencements (10 ans)",
            "Autre"
        ])

    if st.button("📊 Générer le tableau", type="primary", use_container_width=True):
        if not nom_bien:
            st.error("⚠ Veuillez renseigner la désignation du bien")
        else:
            with st.spinner("Calcul en cours..."):
                from datetime import datetime
                date_acq = datetime.combine(date_acquisition, datetime.min.time())

                if mode == "Linéaire":
                    tableau = calculer_amortissement_lineaire(valeur_origine, duree_ans, date_acq)
                else:
                    tableau = calculer_amortissement_degressif(valeur_origine, duree_ans, date_acq)

                st.markdown(f"## 📋 {nom_bien} — Amortissement {mode}")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("💰 Valeur origine", f"{valeur_origine:,.2f} €")
                with col2:
                    st.metric("⏱ Durée", f"{duree_ans} ans")
                with col3:
                    taux = 100 / duree_ans
                    st.metric("📊 Taux", f"{taux:.2f}%")
                with col4:
                    dotation = tableau['Dotation (€)'].iloc[0]
                    st.metric("📅 Dotation/an", f"{dotation:,.2f} €")

                st.divider()
                st.dataframe(tableau, use_container_width=True, hide_index=True)

                # Graphique VNC
                st.markdown("### 📈 Évolution de la VNC")
                col_vnc = 'VNC (€)' if 'VNC (€)' in tableau.columns else 'VNC Fin (€)'
                st.line_chart(tableau.set_index('Année')[col_vnc])

                st.divider()

                # Écritures comptables
                st.markdown("### 📚 Écritures Comptables d'Amortissement")
                st.caption("Compte 6811 — Dotations aux amortissements / 28xx — Amortissements")

                from utils.immobilisations import generer_ecritures_amortissement
                df_ecritures = generer_ecritures_amortissement(nom_bien, tableau)

                annee_courante = datetime.now().year
                col1, col2, col3 = st.columns(3)
                with col1:
                    dotation_courante = df_ecritures[
                        df_ecritures['Année'] == annee_courante
                    ]['Débit (€)'].sum()
                    st.metric("📅 Dotation exercice en cours", f"{dotation_courante:,.2f} €")
                with col2:
                    total_amorti = df_ecritures[
                        df_ecritures['Statut'].str.contains('Passé|cours', na=False)
                    ]['Débit (€)'].sum()
                    st.metric("📉 Total amorti à ce jour", f"{total_amorti:,.2f} €")
                with col3:
                    vnc_col = 'VNC (€)' if 'VNC (€)' in tableau.columns else 'VNC Fin (€)'
                    vnc_actuelle = tableau[tableau['Année'] == annee_courante][vnc_col].values
                    vnc_val = vnc_actuelle[0] if len(vnc_actuelle) > 0 else 0
                    st.metric("💼 VNC actuelle", f"{vnc_val:,.2f} €")

                st.dataframe(df_ecritures, use_container_width=True, hide_index=True)

                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Sauvegarder", use_container_width=True):
                        rapport = generer_rapport_immobilisation(nom_bien, tableau, mode)
                        sauvegarder_si_autorise(type_analyse="Immobilisation", resultat=rapport)
                        st.success("✅ Sauvegardé !")
                with col2:
                    rapport = generer_rapport_immobilisation(nom_bien, tableau, mode)
                    try:
                        generer_bouton_word(f"Amortissement_{nom_bien}", rapport)
                    except Exception as e:
                        st.error(f"Erreur : {e}")

# ── ONGLET 2 : CESSION / SORTIE ──
with onglet2:
    st.markdown("### 🔄 Calcul de Cession / Sortie d'immobilisation")

    col1, col2 = st.columns(2)
    with col1:
        nom_bien_c = st.text_input("🏷 Désignation", placeholder="Ex: Véhicule X", key="cess_nom")
        valeur_origine_c = st.number_input("💰 Valeur d'origine (€)", min_value=0.0, value=10000.0, key="cess_vo")
        amort_cumule = st.number_input("📉 Amortissements cumulés (€)", min_value=0.0, value=6000.0, key="cess_amort")
    with col2:
        prix_cession = st.number_input("💵 Prix de cession (€)", min_value=0.0, value=5000.0, key="cess_prix")
        date_cession = st.date_input("📅 Date de cession", key="cess_date")
        taux_is = st.number_input("🏛 Taux IS (%)", min_value=0, max_value=100, value=25, key="cess_is")

    if st.button("🔄 Calculer la cession", type="primary", use_container_width=True):
        with st.spinner("Calcul en cours..."):
            result = calculer_cession(valeur_origine_c, amort_cumule, prix_cession, date_cession, taux_is)

            st.markdown(f"## 🔄 Cession — {nom_bien_c}")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📦 Valeur origine", f"{result['valeur_origine']:,.2f} €")
            with col2:
                st.metric("📉 VNC", f"{result['vnc']:,.2f} €")
            with col3:
                delta_color = "normal" if result['resultat_cession'] > 0 else "inverse"
                st.metric(
                    result['type_resultat'],
                    f"{abs(result['resultat_cession']):,.2f} €",
                    delta=result['type_resultat'],
                    delta_color=delta_color
                )
            with col4:
                st.metric("🏛 IS estimé", f"{result['impot_estime']:,.2f} €")

            if result['resultat_cession'] > 0:
                st.success(f"✅ **Plus-value de cession** : {result['resultat_cession']:,.2f} €")
            else:
                st.warning(f"⚠ **Moins-value de cession** : {abs(result['resultat_cession']):,.2f} €")

            st.divider()
            st.markdown("### 📚 Écritures Comptables")
            st.dataframe(result['ecritures'], use_container_width=True, hide_index=True)

            st.divider()
            if st.button("💾 Sauvegarder la cession", use_container_width=True):
                rapport_c = f"Cession {nom_bien_c} : {result['type_resultat']} {result['resultat_cession']:,.2f} €"
                sauvegarder_si_autorise(type_analyse="Cession Immobilisation", resultat=rapport_c)
                st.success("✅ Sauvegardé !")

# ── ONGLET 3 : PLAN D'INVESTISSEMENT ──
with onglet3:
    st.markdown("### 📊 Plan d'investissement — Suivi du parc")
    st.caption("Uploadez un fichier Excel avec vos immobilisations")

    uploaded_file = st.file_uploader(
        "📎 Fichier immobilisations (CSV, XLSX)",
        type=["csv", "xlsx"],
        help="Colonnes attendues : Désignation, Valeur, Date acquisition, Durée, Amort. cumulé"
    )

    if uploaded_file:
        df, erreur = charger_fichier(uploaded_file)
        if erreur:
            st.error(f"❌ Erreur : {erreur}")
        else:
            st.success(f"✅ {len(df)} immobilisation(s) chargée(s)")
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.divider()
            st.markdown("### 📊 Analyse du parc")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📦 Nombre de biens", len(df))
            with col2:
                if 'Valeur' in df.columns:
                    st.metric("💰 Valeur totale", f"{pd.to_numeric(df['Valeur'], errors='coerce').sum():,.2f} €")
            with col3:
                if 'Amort. cumulé' in df.columns:
                    st.metric("📉 Amort. total", f"{pd.to_numeric(df['Amort. cumulé'], errors='coerce').sum():,.2f} €")
    else:
        st.info("💡 Vous pouvez aussi saisir vos immobilisations manuellement via l'onglet Tableau d'amortissement.")
# -----------------------------------------------------------------------------
# INVENTAIRE & CLÔTURE
# -----------------------------------------------------------------------------

