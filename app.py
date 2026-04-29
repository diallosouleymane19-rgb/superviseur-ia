elif menu == "Veille fiscale":
    st.subheader("📰 Veille fiscale automatisée")

    # --- 1) Rappel automatique des échéances fiscales ---
    import datetime
    mois = datetime.datetime.now().strftime("%B %Y")

    st.write(f"### 📅 Échéances fiscales – {mois}")

    echeances = [
        "🔸 **TVA** : Déclaration CA3 (régime réel normal) – le 19 ou le 24 selon mode de paiement",
        "🔸 **TVA** : Régime simplifié – acompte trimestriel si applicable",
        "🔸 **DSN** : Déclaration sociale nominative – le 5 ou le 15",
        "🔸 **IS** : Acompte trimestriel (si CA > 250k€) – 15 du mois",
        "🔸 **CFE** : Paiement du solde (décembre) ou acompte (juin)",
        "🔸 **CVAE** : Déclaration et paiement (si applicable)",
        "🔸 **IR** : Retenue à la source – reversement mensuel",
    ]

    for e in echeances:
        st.write(e)

    st.markdown("---")

    # --- 2) Analyse fiscale IA ---
    question = st.text_area("Pose une question fiscale :", height=150)

    if st.button("Analyser la question"):
        if question.strip():
            st.info("Analyse en cours…")
            prompt = f"""
Tu es un fiscaliste français. Réponds clairement et cite les règles applicables.

Question :
{question}

Donne une réponse structurée :
- règle fiscale applicable
- références (CGI, BOFiP si possible)
- risques fiscaux
- conseils pratiques
            """

            reponse = appel_mistral(prompt)

            st.write("### Réponse :")
            st.write(reponse)
        else:
            st.warning("Veuillez entrer une question.")
