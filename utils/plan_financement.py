# -*- coding: utf-8 -*-
"""
Module Plan de Financement PCG France — SMD Consulting
Version Optimisée : KPI, Waterfall et Alertes intégrées
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO

# ─── Fonctions de calcul (Logique métier) ────────────────────────────────────

def extraire_caf_bfr_pcg(fichier_bytes: bytes, nom_fichier: str) -> dict:
    """Extrait CAF et BFR depuis une balance PCG France."""
    try:
        df = pd.read_excel(BytesIO(fichier_bytes)) if nom_fichier.endswith(".xlsx") else pd.read_csv(BytesIO(fichier_bytes), sep=None, engine="python")
        df.columns = [str(c).strip().lower() for c in df.columns]
        col_cpte = next((c for c in df.columns if any(k in c for k in ["compte", "cpte", "n°"])), None)
        col_sol = next((c for c in df.columns if any(k in c for k in ["solde", "credit", "crédit", "montant"])), None)

        if not col_cpte: return {}
        df[col_cpte] = df[col_cpte].astype(str).str.strip()

        def somme(prefixes):
            mask = df[col_cpte].str.startswith(tuple(prefixes), na=False)
            return abs(df.loc[mask, col_sol].apply(pd.to_numeric, errors="coerce").fillna(0).sum()) if col_sol else 0.0

        resultat_net = somme(["120", "121"]) - somme(["129"])
        caf = resultat_net + somme(["681", "682", "686", "687"]) - somme(["781", "786", "787"])
        bfr = somme(["3"]) + somme(["411", "409", "413"]) - somme(["401", "403", "421", "431", "437", "441", "443", "444", "445", "447"])

        return {"CAF estimée": max(caf, 0), "Variation BFR estimée": abs(bfr)}
    except: return {}

def calculer_kpi_financiers(df_r, df_e, annees):
    """Calcule les ratios et détecte les déficits pour chaque année."""
    kpis = {}
    for a in annees:
        tr, te = df_r[a].sum(), df_e[a].sum()
        solde = tr - te
        ratio = (te / tr * 100) if tr != 0 else 0
        kpis[a] = {"solde": solde, "ratio": ratio, "alerte": solde < 0}
    return kpis

# ─── Fonctions de visualisation ──────────────────────────────────────────────

def generer_graphique_waterfall(df_r, df_e, annee):
    """Génère le graphique cascade de financement pour une année."""
    # Note : On utilise ici les sommes par catégorie pour la cascade
    fig = go.Figure(go.Waterfall(
        name="Plan", orientation="v",
        measure=["relative", "relative", "total", "relative", "relative", "total"],
        x=["CAF/Capital", "Emprunts", "Ressources Totales", "Investissements", "Remboursements", "Solde"],
        y=[df_r[annee].iloc[0], df_r[annee].iloc[4], 0, -df_e[annee].iloc[1], -df_e[annee].iloc[3], 0],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
    ))
    fig.update_layout(
        title=f"Flux de financement {annee}", 
        height=400, 
        margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

# ─── Fonctions d'export ──────────────────────────────────────────────────────

def export_excel_complet(df_r, df_e, annees, entreprise):
    """Génère le fichier Excel avec styles."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_r.to_excel(writer, sheet_name="Ressources", index=False)
        df_e.to_excel(writer, sheet_name="Emplois", index=False)
        # Vous pouvez ajouter ici la feuille 'Synthèse' avec les calculs de solde
    return buf.getvalue()
