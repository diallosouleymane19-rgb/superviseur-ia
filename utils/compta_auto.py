def analyse_balance_ai(df):
    """
    Analyse IA de la balance comptable.
    """

    # Limiter la taille du prompt pour éviter HTTP 422
    balance_txt = df.head(50).to_string()

    prompt = f"""
Tu es un expert-comptable français. Analyse la balance suivante :

{balance_txt}

Donne une analyse structurée comprenant :
- points forts
- anomalies
- comptes à surveiller
- suggestions de régularisation
- risques fiscaux
- cohérence des soldes
- remarques professionnelles

Réponds en texte clair, structuré et professionnel.
    """

    reponse = appel_mistral(prompt)
    return reponse
