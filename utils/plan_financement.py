import pandas as pd
from io import BytesIO
import plotly.graph_objects as go


def extraire_caf_bfr_pcg(file_content, filename):
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(BytesIO(file_content), sep=None, engine="python")
        else:
            df = pd.read_excel(BytesIO(file_content))

        df.columns = [str(c).strip().lower() for c in df.columns]
        col_compte = next((c for c in df.columns if "compte" in c or "n°" in c), None)
        col_solde = next((c for c in df.columns if "solde" in c or "débit" in c or "credit" in c), None)

        if col_compte is None or col_solde is None:
            return {}

        df[col_compte] = df[col_compte].astype(str)
        df[col_solde] = pd.to_numeric(df[col_solde], errors="coerce").fillna(0)

        resultat = df[df[col_compte].str.startswith("12")][col_solde].sum()
        dotations = df[df[col_compte].str.startswith("681")][col_solde].sum()
        reprises = df[df[col_compte].str.startswith("781")][col_solde].sum()
        caf = resultat + dotations - reprises

        stocks = df[df[col_compte].str.startswith("3")][col_solde].sum()
        clients = df[df[col_compte].str.startswith("41")][col_solde].sum()
        fournisseurs = df[df[col_compte].str.startswith("40")][col_solde].sum()
        bfr = stocks + clients - fournisseurs

        return {
            "CAF estimée": round(caf, 2),
            "BFR estimé": round(bfr, 2),
            "Stocks": round(stocks, 2),
            "Clients": round(clients, 2),
            "Fournisseurs": round(fournisseurs, 2),
        }
    except Exception:
        return {}


def calculer_kpi_financiers(df_r, df_e, annees):
    kpis = {}
    cumul = 0
    for annee in annees:
        total_r = df_r[annee].sum() if annee in df_r.columns else 0
        total_e = df_e[annee].sum() if annee in df_e.columns else 0
        solde = total_r - total_e
        cumul += solde
        ratio = round((total_e / total_r * 100), 1) if total_r > 0 else 0
        kpis[annee] = {
            "total_ressources": total_r,
            "total_emplois": total_e,
            "solde": solde,
            "tresorerie_cumulee": cumul,
            "ratio": ratio,
            "alerte": solde < 0 or cumul < 0,
        }
    return kpis


def generer_graphique_waterfall(df_r, df_e, annee):
    """Génère un graphique waterfall pour une année donnée."""
    labels_r = df_r.index.tolist()
    vals_r = df_r[annee].tolist() if annee in df_r.columns else [0] * len(labels_r)

    labels_e = df_e.index.tolist()
    vals_e = [-v for v in (df_e[annee].tolist() if annee in df_e.columns else [0] * len(labels_e))]

    labels = labels_r + labels_e
    vals = vals_r + vals_e
    colors = ["steelblue"] * len(labels_r) + ["salmon"] * len(labels_e)

    fig = go.Figure(go.Bar(
        x=labels,
        y=vals,
        marker_color=colors,
        text=[f"{v:,.0f} €" for v in vals],
        textposition="outside"
    ))

    fig.update_layout(
        title=f"Ressources vs Emplois — {annee}",
        xaxis_title="",
        yaxis_title="€",
        showlegend=False,
        height=400
    )
    return fig


def export_excel_complet(df_r, df_e, annees, entreprise):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_r.to_excel(writer, sheet_name="Ressources", index=False)
        df_e.to_excel(writer, sheet_name="Emplois", index=False)
    return buf.getvalue()


def generer_conseils_experts(kpis, annee):
    data = kpis.get(annee)
    if not data:
        return "Données insuffisantes pour l'analyse."

    solde = data["solde"]
    ratio = data["ratio"]
    cumul = data["tresorerie_cumulee"]
    conseils = []

    if solde < 0:
        conseils.append(
            f"🔴 **Alerte Solde** : Déficit de {abs(solde):,.0f} € — "
            "les emplois dépassent les ressources. Augmentez l'apport ou réduisez les investissements."
        )
    else:
        conseils.append(
            f"🟢 **Équilibre Financier** : Solde positif de {solde:,.0f} € — "
            "les ressources couvrent les emplois."
        )

    if cumul < 0:
        conseils.append(
            f"⚠️ **Trésorerie Cumulée Négative** : {cumul:,.0f} € — "
            "revoir la structure (allonger la durée, augmenter l'apport)."
        )

    if ratio > 80:
        conseils.append(
            "⚠️ **Pression Investissement** : Les emplois > 80 % des ressources — marge de sécurité faible."
        )
    elif ratio < 15:
        conseils.append(
            "💡 **Potentiel** : Taux d'emploi faible — ressources disponibles pour investir."
        )

    return "\n\n".join(conseils)
