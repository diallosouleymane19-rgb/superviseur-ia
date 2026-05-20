# -*- coding: utf-8 -*-
"""
Module Plan de Financement PCG France — SMD Consulting
Version optimisée : KPI, Alertes et Visualisations Waterfall
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO

# ─── Fonctions de calcul (Logique métier PCG) ───────────────────────────────

def extraire_caf_bfr_pcg(fichier_bytes: bytes, nom_fichier: str) -> dict:
    """Extrait CAF et BFR depuis une balance PCG France."""
    try:
        # Lecture du fichier
        if nom_fichier.endswith(".xlsx"):
            df = pd.read_excel(BytesIO(fichier_bytes))
        else:
            df = pd.read_csv(BytesIO(fichier_bytes), sep=None, engine="python")
        
        df.columns = [str(c).strip().lower() for c in df.columns]
        col_cpte = next((c for c in df.columns if any(k in c for k in ["compte", "cpte", "n°"])), None)
        col_sol = next((c for c in df.columns if any(k in c for k in ["solde", "credit", "crédit", "montant"])), None)

        if not col_cpte or not col_sol: return {}

        df[col_cpte] = df[col_cpte].astype(str).str.strip()
        df[col_sol] = pd.to_numeric(df[col_sol], errors="coerce").fillna(0)

        def somme(prefixes):
            return df[df[col_cpte].str.startswith(tuple(prefixes), na=False)][col_sol].sum()

        # Calcul PCG France
        resultat_net = somme(["120", "121"]) - somme(["129"])
        dotations = somme(["681", "682", "686", "687"])
        reprises = somme(["781", "786", "787"])
        
        caf = resultat_net + dotations - reprises
        
        # BFR = Stocks + Créances - Dettes d'exploitation
        actif_circ = somme(["3", "411", "409"])
        passif_circ = somme(["401", "403", "421", "431", "441", "445"])
        bfr = actif_circ - passif_circ

        return {"CAF estimée": max(caf, 0), "Variation BFR estimée": bfr}
    except Exception:
        return {}

def calculer_kpi_financiers(df_r, df_e, annees):
    """Calcule les ratios et détecte les déficits."""
    kpis = {}
    for a in annees:
        tr, te = df_r[a].sum(), df_e[a].sum()
        solde = tr - te
        ratio = (te / tr * 100) if tr != 0 else 0
        kpis[a] = {"solde": solde, "ratio": ratio, "alerte": solde < 0}
    return kpis

# ─── Fonctions de visualisation ──────────────────────────────────────────────

def generer_graphique_waterfall(df_r, df_e, annee):
    """Génère le graphique cascade de financement."""
    fig = go.Figure(go.Waterfall(
        name="Plan", orientation="v",
        measure=["relative", "relative", "total", "relative", "relative", "total"],
        x=["CAF", "Emprunts", "Ressources Totales", "Investissements", "Remboursements", "Solde"],
        y=[df_r[annee].iloc[0], df_r[annee].iloc[4], 0, -df_e[annee].iloc[1], -df_e[annee].iloc[3], 0],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
    ))
    fig.update_layout(
        title=f"Cascade de financement {annee}", 
        height=350, 
        margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

# ─── Export Excel ────────────────────────────────────────────────────────────
def export_excel_complet(df_r, df_e, annees, entreprise):
    """Génère le fichier Excel avec styles."""
    buf = BytesIO()
   def export_excel_complet(df_r, df_e, annees, entreprise):
        df_r.to_excel(writer, sheet_name="Ressources", index=False)
        df_e.to_excel(writer, sheet_name="Emplois", index=False)
    return buf.getvalue()


def generer_conseils_experts(kpis, annee):
    """Génère une analyse narrative et des conseils stratégiques."""
    data = kpis.get(annee)
    if not data:
        return "Données insuffisantes pour l'analyse."

    solde = data['solde']
    ratio = data['ratio']

    conseils = []

    if solde < 0:
        conseils.append("🔴 **Alerte Solde** : Le plan est en déficit de financement. Il est impératif de restructurer la dette ou de différer les investissements non prioritaires.")
    else:
        conseils.append("🟢 **Autonomie Financière** : La structure génère un surplus permettant de couvrir le BFR et les investissements.")

    if ratio > 80:
        conseils.append("⚠️ **Pression Investissement** : Le taux est très élevé. Assurez-vous que les retours sur investissement (ROI) sont rapides pour éviter un effet de ciseau sur la trésorerie.")
    elif ratio < 15:
        conseils.append("💡 **Potentiel Stratégique** : Le taux est faible. Envisagez de réinvestir les excédents dans la modernisation des outils de production.")

    return "\n\n".join(conseils)
