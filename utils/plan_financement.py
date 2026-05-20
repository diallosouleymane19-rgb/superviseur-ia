elif page == "📐 Plan de Financement":
    st.subheader("📐 Plan de Financement Pluriannuel")

    # --- Mode de saisie ---
    mode = st.radio(
        "Mode de saisie",
        ["✏️ Saisie manuelle", "📂 Import balance PCG"],
        horizontal=True
    )

    prefill = {}

    if mode == "📂 Import balance PCG":
        with st.expander("📂 Import Balance PCG pour automatisation", expanded=True):
            f = st.file_uploader("Déposer la balance", type=["csv", "xlsx"])
            if f:
                try:
                    prefill = extraire_caf_bfr_pcg(f.read(), f.name)
                    st.success("✅ Balance importée avec succès")
                    st.json(prefill)
                except Exception as e:
                    st.error(f"Erreur import : {e}")

    # --- Saisie manuelle par année ---
    if mode == "✏️ Saisie manuelle":
        st.markdown("#### 📥 RESSOURCES — Saisie par année")
        ressources_data = {"Libellé": ["CAF prévisionnelle", "Augmentation de capital", "Subventions", "Nouveaux emprunts", "Autres ressources"]}

        cols_r = st.columns(len(annees))
        caf_vals, cap_vals, sub_vals, emp_vals, aut_r_vals = [], [], [], [], []
        for i, annee in enumerate(annees):
            with cols_r[i]:
                st.markdown(f"**{annee}**")
                caf_vals.append(st.number_input(f"CAF {annee}", min_value=0, value=0, step=1000, key=f"caf_{annee}"))
                cap_vals.append(st.number_input(f"Capital {annee}", min_value=0, value=0, step=1000, key=f"cap_{annee}"))
                sub_vals.append(st.number_input(f"Subventions {annee}", min_value=0, value=0, step=500, key=f"sub_{annee}"))
                emp_vals.append(st.number_input(f"Emprunts {annee}", min_value=0, value=0, step=1000, key=f"emp_{annee}"))
                aut_r_vals.append(st.number_input(f"Autres {annee}", min_value=0, value=0, step=500, key=f"autr_{annee}"))

        for annee, c, ca, s, e, a in zip(annees, caf_vals, cap_vals, sub_vals, emp_vals, aut_r_vals):
            ressources_data[annee] = [c, ca, s, e, a]

        st.markdown("#### 📤 EMPLOIS — Saisie par année")
        emplois_data = {"Libellé": ["Investissements", "Remboursement emprunt", "Remboursement BPI", "Dividendes", "Variation BFR"]}

        cols_e = st.columns(len(annees))
        inv_vals, remb_vals, bpi_vals, div_vals, bfr_vals = [], [], [], [], []
        for i, annee in enumerate(annees):
            with cols_e[i]:
                st.markdown(f"**{annee}**")
                inv_vals.append(st.number_input(f"Investissements {annee}", min_value=0, value=0, step=1000, key=f"inv_{annee}"))
                remb_vals.append(st.number_input(f"Remb. emprunt {annee}", min_value=0, value=0, step=1000, key=f"remb_{annee}"))
                bpi_vals.append(st.number_input(f"Remb. BPI {annee}", min_value=0, value=0, step=500, key=f"bpi_{annee}"))
                div_vals.append(st.number_input(f"Dividendes {annee}", min_value=0, value=0, step=500, key=f"div_{annee}"))
                bfr_vals.append(st.number_input(f"Variation BFR {annee}", min_value=0, value=0, step=500, key=f"bfr_{annee}"))

        for annee, i, r, b, d, bf in zip(annees, inv_vals, remb_vals, bpi_vals, div_vals, bfr_vals):
            emplois_data[annee] = [i, r, b, d, bf]

        df_r = pd.DataFrame(ressources_data)
        df_e = pd.DataFrame(emplois_data)

    else:
        # Mode import — tableaux éditables avec prefill
        st.markdown("#### 📥 RESSOURCES")
        df_r = st.data_editor(pd.DataFrame({
            "Libellé": ["CAF prévisionnelle", "Augmentation de capital", "Subventions", "Nouveaux emprunts", "Autres ressources"],
            **{a: [prefill.get("CAF estimée", 0)] + [0, 0, 0, 0] for a in annees}
        }), use_container_width=True, key="editor_r")

        st.markdown("#### 📤 EMPLOIS")
        df_e = st.data_editor(pd.DataFrame({
            "Libellé": ["Investissements", "Remboursement emprunt", "Remboursement BPI", "Dividendes", "Variation BFR"],
            **{a: [0, 0, 0, 0, 0] for a in annees}
        }), use_container_width=True, key="editor_e")

    # --- Calculs et affichage ---
    st.markdown("---")
    st.markdown("### 📊 Résultats du Plan de Financement")

    totaux_r = {a: df_r[a].sum() for a in annees}
    totaux_e = {a: df_e[a].sum() for a in annees}
    soldes = {a: totaux_r[a] - totaux_e[a] for a in annees}

    tresorerie_cumulee = []
    cumul = 0
    for a in annees:
        cumul += soldes[a]
        tresorerie_cumulee.append(cumul)

    df_resultats = pd.DataFrame({
        "Année": annees,
        "Total Ressources (€)": [totaux_r[a] for a in annees],
        "Total Emplois (€)": [totaux_e[a] for a in annees],
        "Solde Annuel (€)": [soldes[a] for a in annees],
        "Trésorerie Cumulée (€)": tresorerie_cumulee
    })

    # Mise en forme conditionnelle
    def colorize(val):
        if isinstance(val, (int, float)):
            color = "color: green" if val >= 0 else "color: red"
            return color
        return ""

    st.dataframe(
        df_resultats.style.applymap(colorize, subset=["Solde Annuel (€)", "Trésorerie Cumulée (€)"]),
        use_container_width=True
    )

    # Alertes
    if any(v < 0 for v in tresorerie_cumulee):
        st.error("⚠️ La trésorerie cumulée devient négative — revoir la structure de financement.")
    else:
        st.success("✅ La trésorerie cumulée reste positive sur toute la période.")

    # Graphique
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_bar(x=annees, y=[totaux_r[a] for a in annees], name="Ressources", marker_color="steelblue")
    fig.add_bar(x=annees, y=[-totaux_e[a] for a in annees], name="Emplois", marker_color="salmon")
    fig.add_scatter(x=annees, y=tresorerie_cumulee, name="Trésorerie cumulée", mode="lines+markers", line=dict(color="green", width=2))
    fig.update_layout(barmode="overlay", title="Plan de Financement Pluriannuel", xaxis_title="Année", yaxis_title="€")
    st.plotly_chart(fig, use_container_width=True)

    # Export Excel
    if st.button("📥 Exporter en Excel"):
        from utils.plan_financement import export_excel_complet
        excel_bytes = export_excel_complet(df_r, df_e, annees, st.session_state.get("entreprise", "Entreprise"))
        st.download_button(
            label="💾 Télécharger le fichier Excel",
            data=excel_bytes,
            file_name="plan_financement.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
