# -*- coding: utf-8 -*-
"""
Module Immobilisations - SMD Global Consulting LLC
Gestion des amortissements, cessions et plan d'investissement
"""
from utils.sig_pcg import nb_fr
from utils.formats import est_tableur, TYPES_BALANCE, TYPES_TABLEUR_CSV
import pandas as pd
import numpy as np
from datetime import datetime


import pandas as pd
from datetime import datetime
from utils.page_helpers import champs_remplis
from utils.page_helpers import (
    bouton_sauvegarde,
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)

def calculer_amortissement_lineaire(valeur_origine, duree_ans, date_acquisition):
    """Tableau d'amortissement linéaire, prorata temporis en jours la première année
    (année de 360 jours, mois de 30 jours) à compter de la date d'acquisition / mise en service."""
    taux = 100 / duree_ans
    
    # 1. Prorata de la première année : jours restants jusqu'au 31/12, convention 30/360
    jours_restants = (30 - min(date_acquisition.day, 30) + 1) + 30 * (12 - date_acquisition.month)
    annuite_an1 = (valeur_origine * (taux / 100)) * (jours_restants / 360)
    
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
    
    # Coefficients fiscaux (CGI, art. 39 A) : 1,25 pour 3 et 4 ans ; 1,75 pour 5 et 6 ans ; 2,25 au-delà
    if duree_ans < 3:
        raise ValueError("Amortissement dégressif impossible pour une durée inférieure à 3 ans (CGI, art. 39 A)")
    coeff = 1.25 if duree_ans <= 4 else 1.75 if duree_ans <= 6 else 2.25
    
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
        
        # Prorata première année : mois entiers depuis le 1er jour du mois d'acquisition (CGI, art. 39 A)
        if annee == 1:
            mois_restants = 12 - date_acquisition.month + 1
            dotation = dotation * mois_restants / 12
        
        dotation = round(dotation, 2)
        if annee == duree_ans:   # dernière annuité : solde exact (pas d'écart d'arrondi)
            dotation = round(valeur_origine - cumul, 2)
        cumul = round(cumul + dotation, 2)
        vnc_fin = max(round(vnc_debut - dotation, 2), 0)
        
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


def calculer_cession(valeur_origine, amort_cumule, prix_cession, date_cession, taux_is=25, pcg_2025=None):
    """Calcule la plus ou moins-value de cession.
    pcg_2025 : exercice ouvert depuis le 01/01/2025 (règlement ANC 2022-06) -> prix en 757, VNC en 657 ;
    sinon 775 / 675. Par défaut, déduit de la date de cession."""
    vnc = valeur_origine - amort_cumule
    resultat_cession = prix_cession - vnc
    
    type_resultat = "Plus-value" if resultat_cession > 0 else "Moins-value"
    impot_estime = max(resultat_cession * taux_is / 100, 0) if resultat_cession > 0 else 0
    
    if pcg_2025 is None:
        pcg_2025 = bool(date_cession) and getattr(date_cession, "year", 0) >= 2025
    cpt_prix, cpt_vnc = ("757", "657") if pcg_2025 else ("775", "675")
    lib_prix = ("Produits des cessions d'immobilisations incorporelles et corporelles" if pcg_2025
                else "Produits des cessions d'éléments d'actif")
    lib_vnc = ("Valeur comptable des immobilisations incorporelles et corporelles cédées" if pcg_2025
               else "Valeur comptable des éléments d'actif cédés")
    # Écritures comptables (PCG) : le prix de cession au crédit, la sortie du bien (VNC) au débit et les 28 soldés ;
    # la plus- ou moins-value résulte de la différence prix - VNC.
    ecritures = [
        {'Compte': '512', 'Libellé': 'Banque (prix de cession)', 'Débit': round(prix_cession, 2), 'Crédit': 0},
        {'Compte': cpt_prix, 'Libellé': lib_prix, 'Débit': 0, 'Crédit': round(prix_cession, 2)},
        {'Compte': '28xx', 'Libellé': 'Amortissements cumulés', 'Débit': round(amort_cumule, 2), 'Crédit': 0},
        {'Compte': cpt_vnc, 'Libellé': lib_vnc, 'Débit': round(vnc, 2), 'Crédit': 0},
        {'Compte': '2xxx', 'Libellé': 'Immobilisation (valeur origine)', 'Débit': 0,
         'Crédit': round(valeur_origine, 2)},
    ]
    
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


def _col_vnc(tableau):
    return 'VNC (€)' if 'VNC (€)' in tableau.columns else 'VNC Fin (€)'


def generer_rapport_immobilisation(bien, tableau, mode, valeur_origine=None, duree_ans=None, date_acquisition=None,
                                   categorie=""):
    """Rapport du plan d'amortissement : paramètres puis tableau annuel."""
    vo = valeur_origine if valeur_origine is not None else float(tableau['Dotation (€)'].sum())
    rapport = [f"# TABLEAU D'AMORTISSEMENT — {bien}",
               f"## Amortissement {mode.lower()}",
               f"*Généré le {datetime.now().strftime('%d/%m/%Y')}*", "", "---", ""]
    rapport.append(f"- **Valeur d'origine** : {nb_fr(vo, 2)} €")
    if categorie and categorie != "Autre":
        rapport.append(f"- **Catégorie** : {categorie}")
    if duree_ans:
        rapport.append(f"- **Durée** : {duree_ans} ans")
    if date_acquisition is not None:
        rapport.append(f"- **Date d'acquisition / mise en service** : {date_acquisition.strftime('%d/%m/%Y')}")
    rapport.append("- **Prorata de la 1re année** : " + (
        "mois entiers depuis le 1er jour du mois d'acquisition (CGI, art. 39 A)" if mode == "Dégressif"
        else "jours restants sur une année de 360 jours"))
    rapport += ["", "## PLAN D'AMORTISSEMENT", "",
                "| Année | Dotation (€) | Amort. cumulé (€) | VNC fin (€) | Statut |",
                "|------:|-------------:|------------------:|------------:|--------|"]
    for _, row in tableau.iterrows():
        statut = str(row['Statut']).replace("✅ ", "").replace("📍 ", "").replace("🔮 ", "").replace("Futur", "À venir")
        rapport.append(f"| {int(row['Année'])} | {nb_fr(row['Dotation (€)'], 2)} | {nb_fr(row['Amort. Cumulé (€)'], 2)} | "
                       f"{nb_fr(row[_col_vnc(tableau)], 2)} | {statut} |")
    rapport.append(f"| **Total** | **{nb_fr(tableau['Dotation (€)'].sum(), 2)}** |  |  |  |")
    rapport += ["", "Écriture annuelle : débit 6811 (dotations aux amortissements), crédit 28xx (amortissements).",
                "", "---", "*SMD Global Consulting LLC - KontrolIA*"]
    return "\n".join(rapport)


def visuels_immobilisation(tableau, valeur_origine, duree_ans, mode):
    """Indicateurs et graphique pour l'export Word (mêmes chiffres qu'à l'écran)."""
    from utils.word_visuels import barres_et_courbe, COULEUR_N
    taux = tableau['Taux Dégressif (%)'].iloc[0] if 'Taux Dégressif (%)' in tableau.columns else 100 / duree_ans
    annee = datetime.now().year
    vnc = tableau[tableau['Année'] == annee][_col_vnc(tableau)]
    ind = [{"libelle": "Valeur d'origine", "valeur": f"{nb_fr(valeur_origine)} €"},
           {"libelle": "Durée / mode", "valeur": f"{duree_ans} ans", "detail": mode.lower()},
           {"libelle": "Taux", "valeur": f"{nb_fr(taux, 2)} %", "detail": ""},
           {"libelle": "Dotation 1re année", "valeur": f"{nb_fr(tableau['Dotation (€)'].iloc[0])} €", "detail": ""}]
    if len(vnc):
        ind.append({"libelle": f"VNC fin {annee}", "valeur": f"{nb_fr(vnc.values[0])} €"})
    libs = [str(int(a)) for a in tableau['Année']]
    g = barres_et_courbe(libs, [("Dotation", list(tableau['Dotation (€)']), COULEUR_N)],
                         ("VNC fin d'année", list(tableau[_col_vnc(tableau)])), "Dotations et valeur nette comptable")
    return ind, [g]


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
    from utils.permissions import compter_analyse
    import pandas as pd
    from datetime import datetime
    from utils.page_helpers import (
        sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
        banniere_demo, is_demo, appel_mistral_securise,
        afficher_rapport, afficher_synthese_score,
    )
    st.title("Immobilisations")
    st.markdown("**Amortissements, Cessions et Plan d'investissement**")
    st.caption("Linéaire, dégressif, plus/moins-value de cession")

    from utils.immobilisations import (
        calculer_amortissement_lineaire,
        calculer_amortissement_degressif,
        calculer_cession,
        generer_rapport_immobilisation
    )

    onglet1, onglet2, onglet3 = st.tabs([
        "Tableau d'amortissement",
        "Cession / sortie",
        "Plan d'investissement"
    ])

    # ── ONGLET 1 : TABLEAU D'AMORTISSEMENT ──
    with onglet1:
        st.markdown("### Tableau d'amortissement")

        col1, col2 = st.columns(2)
        with col1:
            nom_bien = st.text_input("Désignation du bien", placeholder="Ex: Véhicule utilitaire")
            valeur_origine = st.number_input("Valeur d'origine (€)", min_value=0.0, value=None, step=100.0,
                                             placeholder="ex. 12 500")
            duree_ans = st.number_input("Durée d'amortissement (ans)", min_value=1, max_value=50, value=5)
        with col2:
            date_acquisition = st.date_input("Date d'acquisition / mise en service", value=None, format="DD/MM/YYYY")
            mode = st.selectbox("Mode d'amortissement", ["Linéaire", "Dégressif"])
            categorie = st.selectbox("Catégorie", [
                "Matériel et outillage (5 ans)",
                "Véhicules (4-5 ans)",
                "Mobilier (10 ans)",
                "Matériel informatique (3 ans)",
                "Constructions (20-50 ans)",
                "Agencements (10 ans)",
                "Autre"
            ])

        if st.button("Générer le tableau", type="primary", width="stretch") and champs_remplis(**{
                "Désignation du bien": nom_bien, "Valeur d'origine": valeur_origine,
                "Date d'acquisition / mise en service": date_acquisition}):
            if mode == "Dégressif" and duree_ans < 3:
                st.error("L'amortissement dégressif n'est possible que pour une durée d'au moins 3 ans "
                         "(CGI, art. 39 A). Choisissez le mode linéaire.", icon=":material/error:")
                st.stop()
            if not compter_analyse("Immobilisations"):
                st.stop()
            with st.spinner("Calcul en cours..."):
                from datetime import datetime
                date_acq = datetime.combine(date_acquisition, datetime.min.time())

                if mode == "Linéaire":
                    tableau = calculer_amortissement_lineaire(valeur_origine, duree_ans, date_acq)
                else:
                    tableau = calculer_amortissement_degressif(valeur_origine, duree_ans, date_acq)

                st.markdown(f"## {nom_bien} — Amortissement {mode}")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Valeur origine", f"{nb_fr(valeur_origine, 2)} €")
                with col2:
                    st.metric("Durée", f"{duree_ans} ans")
                with col3:
                    taux = tableau['Taux Dégressif (%)'].iloc[0] if 'Taux Dégressif (%)' in tableau.columns \
                        else 100 / duree_ans
                    st.metric("Taux", f"{nb_fr(taux, 2)} %")
                with col4:
                    dotation = tableau['Dotation (€)'].iloc[0]
                    st.metric("Dotation/an", f"{nb_fr(dotation, 2)} €")

                st.divider()
                st.dataframe(tableau, width="stretch", hide_index=True)

                # Graphique VNC
                st.markdown("### Évolution de la VNC")
                col_vnc = 'VNC (€)' if 'VNC (€)' in tableau.columns else 'VNC Fin (€)'
                import plotly.graph_objects as go
                annees_g = [str(int(a)) for a in tableau['Année']]
                fig_vnc = go.Figure()
                fig_vnc.add_bar(x=annees_g, y=tableau['Dotation (€)'], name="Dotation", marker_color="#1c5cab")
                fig_vnc.add_scatter(x=annees_g, y=tableau[col_vnc], name="VNC fin d'année", mode="lines+markers",
                                    line=dict(color="#52514e", width=2))
                fig_vnc.update_layout(height=340, yaxis_title="Montant (€)", yaxis_tickformat=",.0f",
                                      xaxis_type="category", legend=dict(orientation="h", y=1.12),
                                      margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_vnc, width="stretch")

                st.divider()

                # Écritures comptables
                st.markdown("### Écritures comptables d'amortissement")
                st.caption("Compte 6811 — Dotations aux amortissements / 28xx — Amortissements")

                from utils.immobilisations import generer_ecritures_amortissement
                df_ecritures = generer_ecritures_amortissement(nom_bien, tableau)

                annee_courante = datetime.now().year
                col1, col2, col3 = st.columns(3)
                with col1:
                    dotation_courante = df_ecritures[
                        df_ecritures['Année'] == annee_courante
                    ]['Débit (€)'].sum()
                    st.metric("Dotation exercice en cours", f"{nb_fr(dotation_courante, 2)} €")
                with col2:
                    total_amorti = df_ecritures[
                        df_ecritures['Statut'].str.contains('Passé|cours', na=False)
                    ]['Débit (€)'].sum()
                    st.metric("Total amorti à ce jour", f"{nb_fr(total_amorti, 2)} €")
                with col3:
                    vnc_col = 'VNC (€)' if 'VNC (€)' in tableau.columns else 'VNC Fin (€)'
                    vnc_actuelle = tableau[tableau['Année'] == annee_courante][vnc_col].values
                    vnc_val = vnc_actuelle[0] if len(vnc_actuelle) > 0 else 0
                    st.metric("VNC actuelle", f"{nb_fr(vnc_val, 2)} €")

                st.dataframe(df_ecritures, width="stretch", hide_index=True)

                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    rapport = generer_rapport_immobilisation(nom_bien, tableau, mode, valeur_origine, duree_ans,
                                                             date_acquisition, categorie)
                    bouton_sauvegarde(type_analyse="Immobilisation", resultat=rapport, libelle="Sauvegarder")
                with col2:
                    try:
                        ind_w, graph_w = visuels_immobilisation(tableau, valeur_origine, duree_ans, mode)
                        generer_bouton_word(f"Amortissement_{nom_bien}", rapport, indicateurs=ind_w,
                                            graphiques=graph_w)
                    except Exception as e:
                        st.error(f"Erreur : {e}")

    # ── ONGLET 2 : CESSION / SORTIE ──
    with onglet2:
        st.markdown("### Calcul de cession / sortie d'immobilisation")

        col1, col2 = st.columns(2)
        with col1:
            nom_bien_c = st.text_input("Désignation", placeholder="Ex: Véhicule X", key="cess_nom")
            valeur_origine_c = st.number_input("Valeur d'origine (€)", min_value=0.0, value=None, key="cess_vo",
                                               placeholder="ex. 10 000")
            amort_cumule = st.number_input("Amortissements cumulés (€)", min_value=0.0, value=None, key="cess_amort",
                                           placeholder="ex. 6 000")
        with col2:
            prix_cession = st.number_input("Prix de cession (€)", min_value=0.0, value=None, key="cess_prix",
                                           placeholder="0 en cas de mise au rebut")
            date_cession = st.date_input("Date de cession", value=None, key="cess_date", format="DD/MM/YYYY")
            taux_is = st.number_input("Taux IS (%)", min_value=0, max_value=100, value=25, key="cess_is")
        pcg_2025 = st.checkbox("Exercice ouvert depuis le 01/01/2025 (plan comptable modifié par le règlement ANC 2022-06)",
                               value=True, key="cess_pcg2025",
                               help="Coché : prix de cession en 757 et valeur comptable en 657 (la cession n'est plus "
                                    "exceptionnelle). Décoché (exercices antérieurs) : 775 et 675.")

        if st.button("Calculer la cession", type="primary", width="stretch") and champs_remplis(**{
                "Valeur d'origine": valeur_origine_c, "Amortissements cumulés": amort_cumule,
                "Prix de cession": prix_cession, "Date de cession": date_cession}):
            if not compter_analyse("Cession"):
                st.stop()
            with st.spinner("Calcul en cours..."):
                result = calculer_cession(valeur_origine_c, amort_cumule, prix_cession, date_cession, taux_is, pcg_2025)

                st.markdown(f"## Cession — {nom_bien_c}")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Valeur origine", f"{nb_fr(result['valeur_origine'], 2)} €")
                with col2:
                    st.metric("VNC", f"{nb_fr(result['vnc'], 2)} €")
                with col3:
                    delta_color = "normal" if result['resultat_cession'] > 0 else "inverse"
                    st.metric(
                        result['type_resultat'],
                        f"{nb_fr(abs(result['resultat_cession']), 2)} €",
                        delta=result['type_resultat'],
                        delta_color=delta_color
                    )
                with col4:
                    st.metric("IS estimé", f"{nb_fr(result['impot_estime'], 2)} €")

                if result['resultat_cession'] > 0:
                    st.success(f"**Plus-value de cession** : {nb_fr(result['resultat_cession'], 2)} €", icon=":material/check_circle:")
                else:
                    st.warning(f"**Moins-value de cession** : {nb_fr(abs(result['resultat_cession']), 2)} €", icon=":material/warning:")

                st.divider()
                st.markdown("### Écritures comptables")
                st.dataframe(result['ecritures'], width="stretch", hide_index=True)

                st.divider()
                rapport_c = f"Cession {nom_bien_c} : {result['type_resultat']} {nb_fr(result['resultat_cession'], 2)} €"
                bouton_sauvegarde(type_analyse="Cession Immobilisation", resultat=rapport_c, libelle="Sauvegarder la cession")
    # ── ONGLET 3 : PLAN D'INVESTISSEMENT ──
    with onglet3:
        st.markdown("### Plan d'investissement — Suivi du parc")
        st.caption("Uploadez un fichier Excel avec vos immobilisations")

        uploaded_file = st.file_uploader(
            "Fichier immobilisations (CSV, XLSX)",
            type=TYPES_TABLEUR_CSV,
            help="Colonnes attendues : Désignation, Valeur, Date acquisition, Durée, Amort. cumulé"
        )

        if uploaded_file and compter_analyse("Parc d'immobilisations", uploaded_file.getvalue()):
            df, erreur = charger_fichier(uploaded_file)
            if erreur:
                st.error(f"Erreur : {erreur}", icon=":material/error:")
            else:
                st.success(f"{len(df)} immobilisation(s) chargée(s)", icon=":material/check_circle:")
                st.dataframe(df, width="stretch", hide_index=True)

                st.divider()
                st.markdown("### Analyse du parc")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Nombre de biens", len(df))
                with col2:
                    if 'Valeur' in df.columns:
                        st.metric("Valeur totale", f"{nb_fr(pd.to_numeric(df['Valeur'], errors='coerce').sum(), 2)} €")
                with col3:
                    if 'Amort. cumulé' in df.columns:
                        st.metric("Amort. total", f"{nb_fr(pd.to_numeric(df['Amort. cumulé'], errors='coerce').sum(), 2)} €")
        else:
            st.info("Vous pouvez aussi saisir vos immobilisations manuellement via l'onglet Tableau d'amortissement.", icon=":material/info:")
    # -----------------------------------------------------------------------------
    # INVENTAIRE & CLÔTURE
    # -----------------------------------------------------------------------------

