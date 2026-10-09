# -*- coding: utf-8 -*-
"""
Module Loi de Benford Professionnel - SMD Global Consulting LLC
Détection d'anomalies statistiques (loi de Benford)
"""
from utils.sig_pcg import nb_fr, nb_fr_signe
from utils.formats import est_tableur, TYPES_BALANCE, TYPES_TABLEUR_CSV
import re
import pandas as pd
import numpy as np
import math
from datetime import datetime
from utils.page_helpers import (
    bouton_sauvegarde,
    sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
    banniere_demo, is_demo, appel_mistral_securise,
    afficher_rapport, afficher_synthese_score,
)

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False

try:
    from scipy import stats
    SCIPY_OK = True
except ImportError:
    SCIPY_OK = False



# Seuils de MAD (écart absolu moyen, en points de %) selon Nigrini, test du premier chiffre
MAD_PARFAIT, MAD_ACCEPTABLE, MAD_MARGINAL = 0.6, 1.2, 1.5


def loi_benford_theorique(digit):
    """Distribution théorique de Benford pour le 1er chiffre (1-9)"""
    return math.log10(1 + 1/digit)


def loi_benford_2eme_chiffre(digit):
    """Distribution théorique pour le 2ème chiffre (0-9)"""
    if digit == 0:
        return sum(math.log10(1 + 1/(10*k + 0)) for k in range(1, 10))
    return sum(math.log10(1 + 1/(10*k + digit)) for k in range(1, 10))


def extraire_premier_chiffre(valeur):
    """Extrait le premier chiffre significatif d'un nombre"""
    try:
        v = abs(float(valeur))
        if v == 0:
            return None
        while v < 1:
            v *= 10
        while v >= 10:
            v //= 10
        return int(v)
    except:
        return None


def extraire_deux_premiers_chiffres(valeur):
    """Extrait les deux premiers chiffres significatifs"""
    try:
        v = abs(float(valeur))
        if v == 0:
            return None
        while v < 10:
            v *= 10
        while v >= 100:
            v //= 10
        return int(v)
    except:
        return None


# ─── Choix des colonnes de montants ─────────────────────────────────────────
DEUX_SENS = "Débit et Crédit (tous les montants)"
_NOM_MONTANT = re.compile(r"(?i)d[ée]bit|cr[ée]dit|montant|solde|amount|valeur|\bttc\b|\bht\b|\btva\b|prix|total")
_NOM_IDENTIFIANT = re.compile(r"(?i)compte|account|\bnum|n°|code|date|journal|pi[eè]ce|r[ée]f|lettr|\bid\b|siren|siret|ann[ée]e|exercice|p[ée]riode|ligne")


def _nombres(serie):
    """Montants lus au format français ou anglais (« 1 234,56 », « 1234.56 », « 1.234,56 »)."""
    from utils.compta_facture import parse_montant
    motif = re.compile(r"\s*[-+−]?\s*[\d\s\u00a0\u202f.,]*\d[\d\s\u00a0\u202f.,]*\s*(€|EUR)?\s*")
    return pd.to_numeric(serie.map(lambda x: parse_montant(str(x).replace("−", "-"))
                                   if pd.notna(x) and motif.fullmatch(str(x)) else None), errors="coerce")


def colonnes_montants(df):
    """Colonnes de montants utilisables pour Benford, les plus probables d'abord.
    Écartées : numéros de compte, dates, codes et références (même s'ils sont numériques)."""
    retenues = []
    for col in df.columns:
        nom = str(col)
        if _NOM_IDENTIFIANT.search(nom) and not _NOM_MONTANT.search(nom):
            continue
        v = _nombres(df[col])
        if v.notna().sum() <= len(df) * 0.5:
            continue
        nz = v[v.notna() & (v != 0)]
        if not _NOM_MONTANT.search(nom) and len(nz):
            # entiers de longueur fixe (comptes, dates AAAAMMJJ, codes) : pas des montants
            txt = df[col].astype(str).str.strip()
            if txt.str.fullmatch(r"\d+").mean() > 0.9 and txt.str.len().nunique() <= 2:
                continue
        retenues.append(nom)
    retenues.sort(key=lambda c: 0 if _NOM_MONTANT.search(c) else 1)
    deb = next((c for c in retenues if re.search(r"(?i)d[ée]bit", c)), None)
    cre = next((c for c in retenues if re.search(r"(?i)cr[ée]dit", c)), None)
    return ([DEUX_SENS] if deb and cre else []) + retenues, (deb, cre)


def valeurs_montants(df, choix, deb_cre=(None, None)):
    """Série des montants non nuls à analyser (les deux colonnes empilées pour « Débit et Crédit »)."""
    if choix == DEUX_SENS:
        v = pd.concat([_nombres(df[deb_cre[0]]), _nombres(df[deb_cre[1]])], ignore_index=True)
    else:
        v = _nombres(df[choix])
    v = v.dropna()
    return v[v != 0]


def analyse_benford_complete(df, col_montant, deb_cre=(None, None)):
    """
    Analyse Benford professionnelle complète
    
    Returns:
        fig: Figure Plotly
        rapport: Rapport markdown
        score_risque: 'Faible', 'Modéré', 'Élevé'
    """
    # Extraction des valeurs
    valeurs = valeurs_montants(df, col_montant, deb_cre)
    
    if len(valeurs) < 30:
        return None, "Échantillon trop faible (minimum 30 valeurs requises)", "Indeterminee"
    
    # ===== 1. ANALYSE DU PREMIER CHIFFRE =====
    premiers_chiffres = valeurs.apply(extraire_premier_chiffre).dropna().astype(int)
    n = len(premiers_chiffres)
    
    distribution_observee = premiers_chiffres.value_counts().sort_index()
    
    # S'assurer qu'on a tous les chiffres 1-9
    for d in range(1, 10):
        if d not in distribution_observee.index:
            distribution_observee[d] = 0
    distribution_observee = distribution_observee.sort_index()
    
    # Frequences observees et theoriques
    freq_observee = distribution_observee / n * 100
    freq_theorique = pd.Series([loi_benford_theorique(d) * 100 for d in range(1, 10)], index=range(1, 10))
    
    # Effectifs
    effectif_observe = distribution_observee
    effectif_theorique = pd.Series([loi_benford_theorique(d) * n for d in range(1, 10)], index=range(1, 10))
    
    # ===== 2. TESTS STATISTIQUES =====
    
    # Test du Chi-carre
    if SCIPY_OK:
        chi2, p_value = stats.chisquare(effectif_observe.values, effectif_theorique.values)
    else:
        # Calcul manuel
        chi2 = sum((effectif_observe.values - effectif_theorique.values)**2 / effectif_theorique.values)
        p_value = None
    
    # MAD - Mean Absolute Deviation
    mad = abs(freq_observee - freq_theorique).mean()
    
    # Interpretation MAD (selon Mark Nigrini)
    # Seuils de Nigrini (premier chiffre) : 0,006 / 0,012 / 0,015 en proportion, soit 0,6 / 1,2 / 1,5 en %
    if mad < MAD_PARFAIT:
        interpretation_mad = "Conformité parfaite"
        risque_mad = "Faible"
    elif mad < MAD_ACCEPTABLE:
        interpretation_mad = "Conformité acceptable"
        risque_mad = "Faible"
    elif mad < MAD_MARGINAL:
        interpretation_mad = "Conformité marginale"
        risque_mad = "Modéré"
    else:
        interpretation_mad = "Non conformité"
        risque_mad = "Élevé"
    
    # Z-scores par chiffre
    z_scores = {}
    for d in range(1, 10):
        ecart = abs(freq_observee[d] - freq_theorique[d])
        ecart_type = math.sqrt(freq_theorique[d] * (100 - freq_theorique[d]) / n)
        z_scores[d] = ecart / ecart_type if ecart_type > 0 else 0
    
    # Detection chiffres anormaux (z > 2.58 = 99% confiance)
    chiffres_anormaux = {d: z for d, z in z_scores.items() if z > 2.58}
    
    # ===== 3. SCORE DE RISQUE GLOBAL =====
    # Combinaison MAD + chi2 + chiffres anormaux
    if mad > MAD_MARGINAL and len(chiffres_anormaux) > 2:
        score_risque = "Élevé"
    elif mad > MAD_ACCEPTABLE or len(chiffres_anormaux) > 1:
        score_risque = "Modéré"
    else:
        score_risque = "Faible"
    
    # ===== 4. VISUALISATION PLOTLY =====
    fig = None
    if PLOTLY_OK:
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=(
                "Distribution observée vs théorique",
                "Z-scores par chiffre"
            )
        )
        
        # Graphique 1 : Barres observees + ligne theorique
        fig.add_trace(
            go.Bar(
                x=list(range(1, 10)),
                y=freq_observee.values,
                name='Observe',
                marker_color='#4A90E2'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=list(range(1, 10)),
                y=freq_theorique.values,
                name='Benford théorique',
                mode='lines+markers',
                marker_color='red',
                line=dict(width=3)
            ),
            row=1, col=1
        )
        
        # Graphique 2 : Z-scores
        couleurs = ['red' if z > 2.58 else 'orange' if z > 1.96 else '#4A90E2' for z in z_scores.values()]
        
        fig.add_trace(
            go.Bar(
                x=list(z_scores.keys()),
                y=list(z_scores.values()),
                name='Z-score',
                marker_color=couleurs,
                showlegend=False
            ),
            row=1, col=2
        )
        
        # Ligne seuil 99%
        fig.add_hline(y=2.58, line_dash="dash", line_color="red", 
                      annotation_text="Seuil 99%", row=1, col=2)
        
        fig.update_xaxes(title_text="Premier chiffre", row=1, col=1)
        fig.update_yaxes(title_text="Fréquence (%)", row=1, col=1)
        fig.update_xaxes(title_text="Chiffre", row=1, col=2)
        fig.update_yaxes(title_text="Z-score", row=1, col=2)
        
        fig.update_layout(
            title_text=f"Analyse Benford - {nb_fr(n, 0)} valeurs analysées",
            height=500,
            showlegend=True
        )
    
    # ===== 5. RAPPORT DETAILLE =====
    rapport = []
    rapport.append("## 📊 ANALYSE LOI DE BENFORD\n")
    rapport.append(f"**Date d'analyse** : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    rapport.append(f"**Échantillon** : {nb_fr(n, 0)} valeurs analysées"
                   + (" (moins de 100 : résultat seulement indicatif)" if n < 100 else ""))
    rapport.append(f"**Colonne** : {col_montant}\n")
    
    # Indicateurs cles
    rapport.append("### 🎯 INDICATEURS CLÉS\n")
    rapport.append(f"- **MAD (écart absolu moyen)** : {nb_fr(mad, 4)} %")
    rapport.append(f"- **Interprétation MAD** : {interpretation_mad}")
    rapport.append(f"- **Chi-carré** : {nb_fr(chi2, 4)}")
    if p_value is not None:
        rapport.append(f"- **P-value** : {nb_fr(p_value, 4)}")
    rapport.append(f"- **Chiffres anormaux (Z>2.58)** : {len(chiffres_anormaux)}")
    rapport.append("")
    
    # Tableau des distributions
    rapport.append("### 📈 DISTRIBUTION DES CHIFFRES\n")
    rapport.append("| Chiffre | Théorique (%) | Observé (%) | Écart | Z-score |")
    rapport.append("|---------|---------------|-------------|-------|---------|")
    for d in range(1, 10):
        ecart = freq_observee[d] - freq_theorique[d]
        rapport.append(f"| {d} | {nb_fr(freq_theorique[d], 2)} | {nb_fr(freq_observee[d], 2)} | {nb_fr_signe(ecart, 2)} | {nb_fr(z_scores[d], 2)} |")
    rapport.append("")
    
    # Chiffres anormaux
    if chiffres_anormaux:
        rapport.append("### ⚠ CHIFFRES SUSPECTS\n")
        for d, z in chiffres_anormaux.items():
            sur_sous = "surreprésenté" if freq_observee[d] > freq_theorique[d] else "sous-représenté"
            rapport.append(f"- **Chiffre {d}** : Z-score = {nb_fr(z, 2)} ({sur_sous})")
        rapport.append("")
    
    # Score et recommandations
    rapport.append(f"### 🚨 SCORE DE RISQUE : **{score_risque.upper()}**\n")
    
    if score_risque == "Faible":
        rapport.append("✅ **Conformité à la loi de Benford** : les données ne présentent pas de signe statistique de manipulation.")
        rapport.append("")
        rapport.append("**Recommandations cabinet :**")
        rapport.append("- Vérification routine - pas d'investigation approfondie nécessaire")
        rapport.append("- Conserver l'analyse dans le dossier de travail")
    
    elif score_risque == "Modéré":
        rapport.append("⚠ **Écarts statistiques détectés** : certains chiffres s'écartent de la distribution théorique.")
        rapport.append("")
        rapport.append("**Recommandations cabinet :**")
        rapport.append("- Examiner les transactions associées aux chiffres anormaux")
        rapport.append("- Vérifier les seuils d'autorisation (souvent à l'origine d'écarts)")
        rapport.append("- Croiser avec une analyse des cycles d'autorisation")
    
    else:  # Eleve
        rapport.append("🚨 **ANOMALIES SIGNIFICATIVES** : la distribution s'écarte fortement de Benford.")
        rapport.append("")
        rapport.append("**Recommandations cabinet :**")
        rapport.append("- **Revue approfondie recommandée**")
        rapport.append("- Examiner les transactions saisies manuellement")
        rapport.append("- Vérifier les seuils d'arrondi et de validation")
        rapport.append("- Analyser les cycles de paiement et autorisations")
        rapport.append("- Croiser avec d'autres contrôles (Z-score, percentiles)")
        rapport.append("- Considérer une enquête sur la fraude potentielle")
    
    rapport.append("")
    rapport.append("---")
    rapport.append("*Analyse générée par SMD Global Consulting LLC - Superviseur IA Comptable*")
    rapport.append("*Méthode : Loi de Benford - 1er chiffre significatif*")
    
    rapport_str = "\n".join(rapport)
    
    return fig, rapport_str, score_risque



def visuels_benford(fig, rapport, score_risque):
    """Indicateurs et graphique pour l'export Word, à partir des mêmes données que l'écran
    (fréquences observées et théoriques du graphique, indicateurs du rapport)."""
    import re
    from utils.word_visuels import benford as graphique_benford
    ton = {"Faible": "bon", "Modéré": "neutre"}.get(score_risque, "mauvais")
    lire = lambda motif: (re.search(motif, rapport) or [None, ""])[1]
    ind = [{"libelle": "Risque", "valeur": score_risque, "ton": ton,
            "detail": {"Faible": "conforme à Benford", "Modéré": "écarts à examiner"}.get(score_risque,
                                                                                         "revue approfondie")},
           {"libelle": "Valeurs analysées", "valeur": lire(r"\*\*Échantillon\*\* : ([\d\s\u202f\u00a0]+)").strip()},
           {"libelle": "MAD", "valeur": lire(r"\*\*MAD \(écart absolu moyen\)\*\* : ([^\n]+)"),
            "detail": lire(r"\*\*Interprétation MAD\*\* : ([^\n]+)")},
           {"libelle": "Chiffres anormaux", "valeur": lire(r"Chiffres anormaux \(Z>2.58\)\*\* : (\d+)"),
            "detail": "Z-score > 2,58"}]
    graphiques = []
    try:
        obs, theo = list(fig.data[0].y), list(fig.data[1].y)
        graphiques.append(graphique_benford(list(range(1, 10)), obs, theo))
    except Exception:
        pass
    return ind, graphiques


def page_benford():
    import streamlit as st
    import pandas as pd
    from datetime import datetime
    from utils.page_helpers import (
        sauvegarder_si_autorise, generer_bouton_word, charger_fichier,
        banniere_demo, is_demo, appel_mistral_securise,
        afficher_rapport, afficher_synthese_score,
    )
    st.title("🛡 Loi de Benford – Détection d'anomalies")
    st.markdown("**Détection statistique** d'anomalies et manipulations de données")
    st.caption("✨ Méthode statistique reconnue pour repérer les montants atypiques à examiner")

    with st.expander("ℹ Comment ça marche ?"):
        st.markdown("""
        **La Loi de Benford** (1938) stipule que dans les données numériques naturelles, 
        le **chiffre 1** apparaît comme premier chiffre dans **30%** des cas, 
        le 2 dans 17,6%, le 3 dans 12,5%, etc.

        ⚠ **Si vos données ne suivent pas cette distribution**, cela peut indiquer :
        - Manipulation manuelle des chiffres
        - Erreurs de saisie systématiques
        - Seuils d'autorisation contournés
        - **Fraude potentielle**

        **Indicateurs analysés** :
        - 📊 **MAD** : Écart moyen absolu (référence Mark Nigrini)
        - 📈 **Chi-carré** : Test statistique de conformité
        - 🎯 **Z-score** par chiffre : détection des anomalies à 99% de confiance
        """)

    uploaded_file = st.file_uploader(
        "📎 Données comptables (FEC, balance : TXT, CSV, Excel)",
        type=TYPES_BALANCE,
        help="FEC, balance, ou tout fichier avec une colonne de montants"
    )

    if uploaded_file:
        df, erreur = charger_fichier(uploaded_file)
        if erreur:
            st.error(f"❌ Erreur lecture fichier : {erreur}")
            st.stop()

        st.success(f"✅ Fichier chargé : **{nb_fr(len(df), 0)} lignes**")

        with st.expander("👀 Aperçu des données"):
            st.dataframe(df.head(10), width="stretch")

        colonnes_num, deb_cre = colonnes_montants(df)
        if colonnes_num:
            col_choix = st.selectbox(
                "🔢 Montants à analyser",
                colonnes_num,
                help="Colonnes de montants détectées. Les numéros de compte, dates, codes et références sont écartés : "
                     "la loi de Benford ne s'applique qu'à des montants."
            )
        else:
            st.warning("Aucune colonne de montants reconnue : choisissez-la vous-même. "
                       "Un numéro de compte, une date ou un code ne convient pas.")
            col_choix = st.selectbox("🔢 Montants à analyser", [str(c) for c in df.columns])
        n_val = len(valeurs_montants(df, col_choix, deb_cre)) if col_choix in colonnes_num or col_choix in df.columns else 0
        st.caption(f"{n_val} montants non nuls à analyser."
                   + (" Moins de 100 : résultat seulement indicatif." if 30 <= n_val < 100 else ""))

        if st.button("🔍 Lancer l'analyse Benford", type="primary", width="stretch"):
            with st.spinner("Analyse statistique en cours..."):
                try:
                    fig, rapport, score_risque = analyse_benford_complete(df, col_choix, deb_cre)
                    if score_risque == "Indeterminee":
                        st.warning(f"⚠ Analyse impossible : {rapport[:1].lower() + rapport[1:].rstrip('.')}. "
                                   "Utilisez un fichier plus détaillé (FEC ou grand livre plutôt qu'une balance courte).")
                        st.stop()

                    st.markdown("## 🎯 Score de Risque")
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if score_risque == "Faible":
                            st.success(f"### ✅ Risque {score_risque}")
                            st.info("**Conformité Benford** - Pas d'anomalie statistique majeure")
                        elif score_risque == "Modéré":
                            st.warning(f"### ⚠ Risque {score_risque}")
                            st.warning("**Écarts détectés** - Investigation recommandée")
                        else:
                            st.error(f"### 🚨 Risque {score_risque}")
                            st.error("**Anomalies significatives** – revue approfondie nécessaire")

                    st.divider()
                    if fig:
                        st.plotly_chart(fig, width="stretch")
                    st.divider()
                    afficher_rapport(rapport, titre="Analyse Statistique Benford", afficher_kpis_auto=True, afficher_alertes_auto=True, compact=True)
                    st.divider()

                    col1, col2 = st.columns(2)
                    with col1:
                        bouton_sauvegarde(type_analyse="Loi de Benford", resultat=rapport, libelle="💾 Sauvegarder")
                    with col2:
                        try:
                            ind_w, graph_w = visuels_benford(fig, rapport, score_risque)
                            generer_bouton_word("Analyse_Benford", rapport, indicateurs=ind_w, graphiques=graph_w)
                        except Exception as e:
                            st.error(f"Erreur : {e}")

                except Exception as e:
                    st.error(f"❌ Erreur : {str(e)}")
                    import traceback
                    with st.expander("Détails techniques"):
                        st.code(traceback.format_exc())
    # -----------------------------------------------------------------------------
    # 6. COMPTE DE RÉSULTAT - VERSION PROFESSIONNELLE CABINET
    # -----------------------------------------------------------------------------

