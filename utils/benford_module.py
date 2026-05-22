# -*- coding: utf-8 -*-
"""
Module Loi de Benford Professionnel - SMD Consulting
Detection de fraude statistique pour Cabinets d'Audit
"""
import pandas as pd
import numpy as np
import math
from datetime import datetime

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


def loi_benford_theorique(digit):
    """Distribution theorique de Benford pour le 1er chiffre (1-9)"""
    return math.log10(1 + 1/digit)


def loi_benford_2eme_chiffre(digit):
    """Distribution theorique pour le 2eme chiffre (0-9)"""
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


def analyse_benford_complete(df, col_montant):
    """
    Analyse Benford professionnelle complete
    
    Returns:
        fig: Figure Plotly
        rapport: Rapport markdown
        score_risque: 'Faible', 'Modere', 'Eleve'
    """
    # Extraction des valeurs
    valeurs = pd.to_numeric(
        df[col_montant].astype(str).str.replace(',', '.').str.replace(' ', ''),
        errors='coerce'
    ).dropna()
    valeurs = valeurs[valeurs != 0]
    
    if len(valeurs) < 30:
        return None, "Echantillon trop faible (minimum 30 valeurs requises)", "Indeterminee"
    
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
    if mad < 0.0006 * 100:
        interpretation_mad = "Conformite parfaite"
        risque_mad = "Faible"
    elif mad < 0.0012 * 100:
        interpretation_mad = "Conformite acceptable"
        risque_mad = "Faible"
    elif mad < 0.0015 * 100:
        interpretation_mad = "Conformite marginale"
        risque_mad = "Modere"
    else:
        interpretation_mad = "Non conformite"
        risque_mad = "Eleve"
    
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
    if mad > 0.0015 * 100 and len(chiffres_anormaux) > 2:
        score_risque = "Eleve"
    elif mad > 0.0012 * 100 or len(chiffres_anormaux) > 1:
        score_risque = "Modere"
    else:
        score_risque = "Faible"
    
    # ===== 4. VISUALISATION PLOTLY =====
    fig = None
    if PLOTLY_OK:
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=(
                "Distribution observee vs theorique",
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
                name='Benford theorique',
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
        fig.update_yaxes(title_text="Frequence (%)", row=1, col=1)
        fig.update_xaxes(title_text="Chiffre", row=1, col=2)
        fig.update_yaxes(title_text="Z-score", row=1, col=2)
        
        fig.update_layout(
            title_text=f"Analyse Benford - {n:,} valeurs analysees",
            height=500,
            showlegend=True
        )
    
    # ===== 5. RAPPORT DETAILLE =====
    rapport = []
    rapport.append("## 📊 ANALYSE LOI DE BENFORD\n")
    rapport.append(f"**Date d'analyse** : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    rapport.append(f"**Echantillon** : {n:,} valeurs analysees")
    rapport.append(f"**Colonne** : {col_montant}\n")
    
    # Indicateurs cles
    rapport.append("### 🎯 INDICATEURS CLES\n")
    rapport.append(f"- **MAD (Mean Absolute Deviation)** : {mad:.4f}%")
    rapport.append(f"- **Interpretation MAD** : {interpretation_mad}")
    rapport.append(f"- **Chi-carre** : {chi2:.4f}")
    if p_value is not None:
        rapport.append(f"- **P-value** : {p_value:.4f}")
    rapport.append(f"- **Chiffres anormaux (Z>2.58)** : {len(chiffres_anormaux)}")
    rapport.append("")
    
    # Tableau des distributions
    rapport.append("### 📈 DISTRIBUTION DES CHIFFRES\n")
    rapport.append("| Chiffre | Theorique (%) | Observe (%) | Ecart | Z-score |")
    rapport.append("|---------|---------------|-------------|-------|---------|")
    for d in range(1, 10):
        ecart = freq_observee[d] - freq_theorique[d]
        rapport.append(f"| {d} | {freq_theorique[d]:.2f} | {freq_observee[d]:.2f} | {ecart:+.2f} | {z_scores[d]:.2f} |")
    rapport.append("")
    
    # Chiffres anormaux
    if chiffres_anormaux:
        rapport.append("### ⚠️ CHIFFRES SUSPECTS\n")
        for d, z in chiffres_anormaux.items():
            sur_sous = "SUR-represente" if freq_observee[d] > freq_theorique[d] else "SOUS-represente"
            rapport.append(f"- **Chiffre {d}** : Z-score = {z:.2f} ({sur_sous})")
        rapport.append("")
    
    # Score et recommandations
    rapport.append(f"### 🚨 SCORE DE RISQUE : **{score_risque.upper()}**\n")
    
    if score_risque == "Faible":
        rapport.append("✅ **Conformite a la loi de Benford** : les donnees ne presentent pas de signe statistique de manipulation.")
        rapport.append("")
        rapport.append("**Recommandations cabinet :**")
        rapport.append("- Verification routine - pas d'investigation approfondie necessaire")
        rapport.append("- Conserver l'analyse pour la documentation d'audit")
    
    elif score_risque == "Modere":
        rapport.append("⚠️ **Ecarts statistiques detectes** : certains chiffres s'ecartent de la distribution theorique.")
        rapport.append("")
        rapport.append("**Recommandations cabinet :**")
        rapport.append("- Examiner les transactions associees aux chiffres anormaux")
        rapport.append("- Verifier les seuils d'autorisation (souvent a l'origine d'ecarts)")
        rapport.append("- Croiser avec une analyse des cycles d'autorisation")
    
    else:  # Eleve
        rapport.append("🚨 **ANOMALIES SIGNIFICATIVES** : la distribution s'ecarte fortement de Benford.")
        rapport.append("")
        rapport.append("**Recommandations cabinet :**")
        rapport.append("- **Audit approfondi recommande**")
        rapport.append("- Examiner les transactions saisies manuellement")
        rapport.append("- Verifier les seuils d'arrondi et de validation")
        rapport.append("- Analyser les cycles de paiement et autorisations")
        rapport.append("- Croiser avec d'autres tests d'audit (Z-score, percentiles)")
        rapport.append("- Considerer une enquete sur la fraude potentielle")
    
    rapport.append("")
    rapport.append("---")
    rapport.append("*Analyse generee par SMD Consulting - Superviseur IA Comptable*")
    rapport.append("*Methode : Loi de Benford - 1er chiffre significatif*")
    
    rapport_str = "\n".join(rapport)
    
    return fig, rapport_str, score_risque