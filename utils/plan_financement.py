# -*- coding: utf-8 -*-
"""
Module Plan de Financement PCG France — SMD Global Consulting LLC
Saisie manuelle + Import balance | Analyse IA Mistral | Export Excel
"""
from utils.sig_pcg import nb_fr
from utils.formats import est_tableur, TYPES_BALANCE, TYPES_TABLEUR_CSV
from utils.security import sanitize_filename
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

try:
    import plotly.graph_objects as go
    _PLOTLY_OK = True
except ImportError:
    _PLOTLY_OK = False

# --- Categories PCG France ---

RESSOURCES = [
    "Capacité d'autofinancement (CAF)",
    "Cessions d'éléments d'actif",
    "Augmentation de capital",
    "Subventions d'investissement reçues",
    "Nouveaux emprunts LT/MT",
    "Autres ressources durables",
]

EMPLOIS = [
    "Acquisitions d'immobilisations incorporelles",
    "Acquisitions d'immobilisations corporelles",
    "Acquisitions d'immobilisations financières",
    "Remboursements d'emprunts",
    "Distribution de dividendes",
    "Variation du besoin en fonds de roulement (BFR)",
    "Autres emplois stables",
]

# --- Helpers ---

@st.cache_data(show_spinner=False)
def _extraire_caf_bfr_pcg(fichier_bytes: bytes, nom_fichier: str) -> dict:
    """CAF (méthode additive PCG) et BFR à la clôture, depuis une balance ou un FEC.
    CAF = résultat net + dotations (681, 686, 687) - reprises (781, 786, 787)
          + VNC des éléments cédés (675) - produits de cession (775) - quote-part de subventions virée (777).
    Résultat net : classe 7 - classe 6 (balance avant affectation), sinon comptes 120 / 129."""
    try:
        from utils.intelligent_parser import charger_balance_ou_fec
        from utils.sig_pcg import _preparer, _solde
        from utils.bilan import calculer_bilan, R_BFR
        f = BytesIO(fichier_bytes)
        f.name = nom_fichier
        df, _, _ = charger_balance_ou_fec(f)
        d = _preparer(df)
        c = lambda p, ex=(): _solde(d, p, ex, "credit")
        db = lambda p, ex=(): _solde(d, p, ex, "debit")

        a_gestion = d["_cpt"].str.match(r"^[67]").any()
        resultat_net = (c(["7"]) - db(["6"])) if a_gestion else (c(["120"]) - db(["129"]))
        caf = (resultat_net + db(["681", "686", "687"]) - c(["781", "786", "787"])
               + db(["675"]) - c(["775"]) - c(["777"]))

        bilan = calculer_bilan(df)
        bfr = None if "erreur" in bilan else bilan["ratios"][R_BFR]
        return {"CAF": caf, "Résultat net": resultat_net, "BFR à la clôture": bfr}
    except Exception:
        return {}


def _chart_plan(df_r: pd.DataFrame, df_e: pd.DataFrame, annees: list):
    if not _PLOTLY_OK:
        return None
    total_r = [df_r[a].sum() for a in annees]
    total_e = [df_e[a].sum() for a in annees]
    solde = [r - e for r, e in zip(total_r, total_e)]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Ressources", x=annees, y=total_r,
                         marker_color="#1E8449",
                         hovertemplate="%{y:,.0f} €<extra>Ressources</extra>"))
    fig.add_trace(go.Bar(name="Emplois", x=annees, y=total_e,
                         marker_color="#C0392B",
                         hovertemplate="%{y:,.0f} €<extra>Emplois</extra>"))
    fig.add_trace(go.Scatter(name="Solde", x=annees, y=solde,
                             mode="lines+markers",
                             line=dict(color="#2C3E50", width=2.5, dash="dot"),
                             marker=dict(size=9),
                             hovertemplate="%{y:,.0f} €<extra>Solde</extra>"))
    fig.add_hline(y=0, line_dash="dash", line_color="#888", line_width=1)
    fig.update_layout(
        title="Plan de financement - Ressources vs Emplois",
        barmode="group", height=420,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.15),
        yaxis_tickformat=",.0f",
    )
    return fig


def _export_excel(df_r: pd.DataFrame, df_e: pd.DataFrame, annees: list, entreprise: str) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        from openpyxl.styles import PatternFill, Font, Alignment
        from openpyxl.utils import get_column_letter

        def _style(ws, header_color):
            for cell in ws[1]:
                cell.fill = PatternFill("solid", fgColor=header_color)
                cell.font = Font(color="FFFFFF", bold=True)
                cell.alignment = Alignment(horizontal="center")
            for col in ws.columns:
                ws.column_dimensions[get_column_letter(col[0].column)].width = 28

        df_r_exp = df_r.copy().set_index("Ressource")
        df_r_exp.loc["TOTAL RESSOURCES"] = df_r_exp[annees].sum()
        df_r_exp.reset_index().to_excel(writer, sheet_name="Ressources", index=False)
        _style(writer.sheets["Ressources"], "1E8449")

        df_e_exp = df_e.copy().set_index("Emploi")
        df_e_exp.loc["TOTAL EMPLOIS"] = df_e_exp[annees].sum()
        df_e_exp.reset_index().to_excel(writer, sheet_name="Emplois", index=False)
        _style(writer.sheets["Emplois"], "C0392B")

        synth = pd.DataFrame({
            "Année": annees,
            "Total Ressources (€)": [df_r[a].sum() for a in annees],
            "Total Emplois (€)": [df_e[a].sum() for a in annees],
            "Solde (€)": [df_r[a].sum() - df_e[a].sum() for a in annees],
        })
        synth.to_excel(writer, sheet_name="Synthèse", index=False)
        _style(writer.sheets["Synthèse"], "2C3E50")

    return buf.getvalue()


def _lignes_tableau(df, col_lib, annees, total_lib):
    lignes = [f"| {col_lib} | " + " | ".join(annees) + " | Total |",
              "|---|" + "---:|" * (len(annees) + 1)]
    for _, r in df.iterrows():
        vals = [float(r[a] or 0) for a in annees]
        if any(vals):
            lignes.append(f"| {r[col_lib]} | " + " | ".join(nb_fr(v) for v in vals) + f" | {nb_fr(sum(vals))} |")
    tot = [float(df[a].sum()) for a in annees]
    lignes.append(f"| **{total_lib}** | " + " | ".join(f"**{nb_fr(v)}**" for v in tot) + f" | **{nb_fr(sum(tot))}** |")
    return lignes


def rapport_plan_financement(df_r, df_e, annees, entreprise):
    """Rapport du plan de financement (Markdown) : lecture en tête, puis ressources, emplois, synthèse annuelle et cumulée."""
    tr = [float(df_r[a].sum()) for a in annees]
    te = [float(df_e[a].sum()) for a in annees]
    solde = [x - y for x, y in zip(tr, te)]
    cumul = [sum(solde[:i + 1]) for i in range(len(solde))]
    deficits = [a for a, v in zip(annees, solde) if v < 0]

    r = [f"# PLAN DE FINANCEMENT – {entreprise}",
         f"## Période {annees[0]} – {annees[-1]}",
         f"*Édité le {datetime.now().strftime('%d/%m/%Y')} · montants en euros*", "", "---", "",
         "## LECTURE", ""]
    if deficits:
        r.append(f"- **Besoin de financement** en {', '.join(deficits)} : les emplois dépassent les ressources. "
                 "Prévoir un financement complémentaire (apport, emprunt, subvention) ou étaler les investissements.")
    else:
        r.append("- **Plan équilibré** : les ressources couvrent les emplois chaque année.")
    if cumul and cumul[-1] < 0:
        r.append(f"- **Solde cumulé négatif** sur la période : {nb_fr(cumul[-1])} €.")
    r += ["", "## RESSOURCES", ""]
    r += _lignes_tableau(df_r, "Ressource", annees, "Total ressources")
    r += ["", "## EMPLOIS", ""]
    r += _lignes_tableau(df_e, "Emploi", annees, "Total emplois")
    r += ["", "## SYNTHÈSE", "", "| | " + " | ".join(annees) + " |", "|---|" + "---:|" * len(annees)]
    r.append("| Total ressources | " + " | ".join(nb_fr(v) for v in tr) + " |")
    r.append("| Total emplois | " + " | ".join(nb_fr(v) for v in te) + " |")
    r.append("| **Solde annuel** | " + " | ".join(f"**{nb_fr(v)}**" for v in solde) + " |")
    r.append("| Solde cumulé | " + " | ".join(nb_fr(v) for v in cumul) + " |")
    r += ["", "---", "*SMD Global Consulting LLC - Superviseur IA Comptable*"]
    return "\n".join(r)

def visuels_plan_financement(df_r, df_e, annees):
    """Indicateurs et graphique pour l'export Word (mêmes chiffres qu'à l'écran)."""
    from utils.word_visuels import barres_et_courbe, COULEUR_N, COULEUR_ORANGE
    tr = [float(df_r[a].sum()) for a in annees]
    te = [float(df_e[a].sum()) for a in annees]
    solde = [x - y for x, y in zip(tr, te)]
    deficits = sum(1 for v in solde if v < 0)
    ind = [{"libelle": "Ressources sur la période", "valeur": f"{nb_fr(sum(tr))} €"},
           {"libelle": "Emplois sur la période", "valeur": f"{nb_fr(sum(te))} €"},
           {"libelle": "Solde cumulé", "valeur": f"{nb_fr(sum(solde))} €", "ton": "bon" if sum(solde) >= 0 else "mauvais",
            "detail": "excédent" if sum(solde) >= 0 else "besoin de financement"},
           {"libelle": "Années en déficit", "valeur": f"{deficits} / {len(annees)}",
            "ton": "mauvais" if deficits else "bon", "detail": "aucune" if not deficits else "à financer"}]
    g = barres_et_courbe(annees, [("Ressources", tr, COULEUR_N), ("Emplois", te, COULEUR_ORANGE)],
                         ("Solde annuel", solde), "Ressources, emplois et solde annuel")
    return ind, [g]


def _analyser_ia(df_r: pd.DataFrame, df_e: pd.DataFrame, annees: list, entreprise: str) -> str:
    try:
        from utils.ai import appel_mistral, extraire_contenu_mistral
        lignes = []
        for a in annees:
            r = df_r[a].sum()
            e = df_e[a].sum()
            lignes.append(f"  {a} : Ressources = {nb_fr(r)} € | Emplois = {nb_fr(e)} € | Solde = {nb_fr(r - e)} €")
        resume = "\n".join(lignes)

        prompt = f"""Tu es expert-comptable PCG France. Analyse ce plan de financement pour {entreprise} :

{resume}

Fournis :
1. Diagnostic de l'équilibre financier (ressources/emplois)
2. Risques identifies (sous-financement, endettement, BFR)
3. Points forts du plan
4. Recommandations concrètes (refinancement, optimisation BFR, fonds propres)
5. Conformité avec les bonnes pratiques PCG

Sois concis et professionnel."""

        result = appel_mistral(prompt, temperature=0.3,
                               noms=[entreprise] if entreprise and entreprise.strip().lower() != "entreprise" else [])
        return extraire_contenu_mistral(result) or "Analyse indisponible."
    except Exception as e:
        return f"Analyse IA indisponible : {e}"


# --- Page principale ---

def page_plan_financement():
    st.title("Plan de Financement")
    st.markdown("*PCG France - Équilibre ressources / emplois sur 1 à 5 ans*")
    st.divider()

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        entreprise = st.text_input("Entreprise", value="Mon Entreprise")
    with col2:
        annee_debut = st.number_input("Année de départ", value=None, placeholder="ex. 2027",
                                       min_value=2000, max_value=2050, step=1)
    with col3:
        nb_annees = st.slider("Nombre d'années", 1, 5, 3)

    if annee_debut is None:
        st.info("Saisissez l'année de départ pour construire le plan de financement.")
        return
    annee_debut = int(annee_debut)
    annees = [str(annee_debut + i) for i in range(nb_annees)]
    st.caption(f"Période : **{annees[0]}** → **{annees[-1]}**")
    st.divider()

    prefill_r: dict = {}
    prefill_e: dict = {}

    with st.expander("Importer une balance PCG pour pré-remplir la CAF"):
        fichier = st.file_uploader("Balance (Excel, LibreOffice, CSV ou TXT)", type=TYPES_BALANCE,
                                    key="balance_plan")
        if fichier:
            with st.spinner("Extraction en cours..."):
                vals = _extraire_caf_bfr_pcg(fichier.read(), fichier.name)
            if vals:
                prefill_r["Capacité d'autofinancement (CAF)"] = max(vals["CAF"], 0.0)
                st.success(f"CAF : {nb_fr(vals['CAF'])} € (résultat net : {nb_fr(vals['Résultat net'])} €), "
                           "reportée dans les ressources.")
                if vals["CAF"] < 0:
                    st.warning("CAF négative : elle n'est pas reportée dans les ressources ; à traiter en emploi si besoin.")
                if vals["BFR à la clôture"] is not None:
                    st.info(f"BFR à la clôture : {nb_fr(vals['BFR à la clôture'])} €. Une seule balance ne donne pas "
                            "sa variation : saisissez la variation du BFR dans les emplois.")
            else:
                st.warning("Extraction impossible - saisissez les valeurs manuellement.")

    st.divider()

    st.subheader("Ressources")
    r_data = {"Ressource": RESSOURCES}
    for a in annees:
        r_data[a] = [prefill_r.get(lib, 0.0) for lib in RESSOURCES]
    df_r = st.data_editor(
        pd.DataFrame(r_data),
        width="stretch",
        hide_index=True,
        column_config={a: st.column_config.NumberColumn(f"{a} (€)", format="localized", min_value=0)
                       for a in annees},
        key="editor_ressources",
    )

    st.divider()

    st.subheader("Emplois")
    e_data = {"Emploi": EMPLOIS}
    for a in annees:
        e_data[a] = [prefill_e.get(lib, 0.0) for lib in EMPLOIS]
    df_e = st.data_editor(
        pd.DataFrame(e_data),
        width="stretch",
        hide_index=True,
        column_config={a: st.column_config.NumberColumn(f"{a} (€)", format="localized", min_value=0)
                       for a in annees},
        key="editor_emplois",
    )

    st.divider()

    st.subheader("Synthèse")
    cols = st.columns(len(annees))
    for i, a in enumerate(annees):
        total_r = df_r[a].sum()
        total_e = df_e[a].sum()
        solde = total_r - total_e
        with cols[i]:
            st.metric(f"Ressources {a}", f"{nb_fr(total_r, 0)} €")
            st.metric(f"Emplois {a}", f"{nb_fr(total_e, 0)} €")
            delta_color = "normal" if solde >= 0 else "inverse"
            st.metric(f"Solde {a}", f"{nb_fr(solde, 0)} €",
                      delta=f"{'Excédent' if solde >= 0 else 'Déficit'}",
                      delta_color=delta_color)

    if _PLOTLY_OK:
        fig = _chart_plan(df_r, df_e, annees)
        if fig:
            st.plotly_chart(fig, width="stretch")
    else:
        st.warning("Graphique indisponible - installez plotly.")

    st.divider()

    col_ia, col_w, col_xl = st.columns(3)

    with col_ia:
        if st.button("Analyse IA du plan", type="primary", width="stretch"):
            with st.spinner("Analyse en cours..."):
                analyse = _analyser_ia(df_r, df_e, annees, entreprise)
            st.markdown("### Analyse IA")
            from utils.page_helpers import afficher_contenu_ia
            afficher_contenu_ia(analyse, "plan_financement")

    with col_w:
        from utils.page_helpers import generer_bouton_word, bouton_sauvegarde
        ind_w, graph_w = visuels_plan_financement(df_r, df_e, annees)
        rapport_w = rapport_plan_financement(df_r, df_e, annees, entreprise)
        generer_bouton_word(f"Plan_de_financement_{entreprise}_{annees[0]}", rapport_w,
                            indicateurs=ind_w, graphiques=graph_w)
        bouton_sauvegarde(type_analyse="Plan de financement", resultat=rapport_w, key="save_plan")

    with col_xl:
        excel_bytes = _export_excel(df_r, df_e, annees, entreprise)
        st.download_button(
            "📥 Exporter Excel",
            data=excel_bytes,
            file_name=sanitize_filename(f"Plan_de_financement_{entreprise}_{annees[0]}") + ".xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
