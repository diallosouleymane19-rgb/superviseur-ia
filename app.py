if page == "🏠 Accueil":
    import plotly.express as px
    import numpy as np

    st.title("🏠 Superviseur IA Comptable")
    st.markdown("### Bienvenue dans votre assistant comptable intelligent")
    st.markdown("---")

    # --- CARTES ---
    col1, col2, col3 = st.columns(3)
    col1.info("🧾 OCR Facture\nExtraction automatique de vos factures")
    col2.info("📊 Analyse Balance\nAnalyse IA de votre balance comptable")
    col3.info("📂 Traitement FEC\nContrôle fiscal de vos écritures")

    st.markdown("---")
    col4, col5, col6 = st.columns(3)
    col4.success("🏦 Rapprochement Bancaire\nComparez banque et comptabilité")
    col5.success("🔗 Cohérence Inter-Documents\nCroisez vos documents comptables")
    col6.success("🚨 Alertes de Gestion\nDétectez les anomalies en temps réel")

    st.markdown("---")
    st.warning("📰 Veille Fiscale — Restez à jour sur la réglementation française")

    st.markdown("---")
    st.subheader("📊 Tableau de Bord")

    # --- GRAPHIQUE 1 : Répartition des charges ---
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Répartition des charges (exemple)**")
        df_charges = pd.DataFrame({
            "Poste": ["Achats", "Salaires", "Loyer", "Impôts", "Autres"],
            "Montant": [45000, 120000, 18000, 12000, 8000]
        })
        fig1 = px.pie(
            df_charges,
            values="Montant",
            names="Poste",
            color_discrete_sequence=px.colors.sequential.Blues_r
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.markdown("**Évolution du chiffre d'affaires (exemple)**")
        df_ca = pd.DataFrame({
            "Mois": ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
                     "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"],
            "CA": [32000, 35000, 41000, 38000, 45000, 52000,
                   48000, 43000, 55000, 61000, 58000, 70000]
        })
        fig2 = px.bar(
            df_ca,
            x="Mois",
            y="CA",
            color="CA",
            color_continuous_scale="Blues"
        )
        st.plotly_chart(fig2, use_container_width=True)

    # --- GRAPHIQUE 2 : Comparaison Charges vs Produits ---
    st.markdown("**Comparaison Charges vs Produits par trimestre (exemple)**")
    df_cp = pd.DataFrame({
        "Trimestre": ["T1", "T2", "T3", "T4"],
        "Charges": [108000, 103000, 110000, 136000],
        "Produits": [108000, 135000, 146000, 189000]
    })
    fig3 = px.line(
        df_cp,
        x="Trimestre",
        y=["Charges", "Produits"],
        markers=True,
        color_discrete_sequence=["#ef553b", "#00cc96"]
    )
    st.plotly_chart(fig3, use_container_width=True)