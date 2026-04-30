import feedparser
from .ai import appel_mistral
from datetime import datetime

# Sources RSS officielles françaises
SOURCES_RSS = {
    "BOFIP - Impots.gouv": "https://bofip.impots.gouv.fr/bofip/flux-rss.html",
    "Légifrance": "https://www.legifrance.gouv.fr/rss/rss_actualite.xml",
    "Economie.gouv.fr": "https://www.economie.gouv.fr/rss.xml",
    "Urssaf": "https://www.urssaf.fr/portail/home/rss.rss",
}

def recuperer_articles_rss():
    """
    Récupère les derniers articles fiscaux depuis les flux RSS officiels.
    """
    articles = []

    for source, url in SOURCES_RSS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:  # 5 derniers articles par source
                titre = entry.get("title", "Sans titre")
                lien = entry.get("link", "")
                date = entry.get("published", "Date inconnue")
                resume = entry.get("summary", "")[:300]

                articles.append({
                    "source": source,
                    "titre": titre,
                    "lien": lien,
                    "date": date,
                    "resume": resume
                })
        except Exception:
            continue

    return articles

def obtenir_veille_fiscale():
    """
    Veille fiscale basée sur les flux RSS officiels + analyse IA.
    """
    try:
        articles = recuperer_articles_rss()

        if not articles:
            return "❌ Impossible de récupérer les flux RSS. Vérifiez votre connexion."

        # Préparer le contexte pour l'IA
        contexte = ""
        for art in articles:
            contexte += f"""
Source : {art['source']}
Titre : {art['titre']}
Date : {art['date']}
Résumé : {art['resume']}
Lien : {art['lien']}
---
"""

        prompt = f"""
Tu es un expert fiscaliste français. Voici les dernières actualités fiscales officielles 
récupérées depuis les sources gouvernementales françaises :

{contexte}

Sur la base de ces informations RÉELLES et RÉCENTES, génère une veille fiscale structurée :

1. 📋 ACTUALITÉS FISCALES RÉCENTES
   - Résume les principales nouveautés législatives
   - Cite les sources officielles

2. 📅 POINTS D'ATTENTION IMMÉDIATS
   - Quelles sont les échéances et obligations urgentes ?
   - Quels changements impactent les entreprises maintenant ?

3. 💼 IMPACT POUR LES ENTREPRISES
   - Ce que les PME/TPE doivent savoir
   - Actions à mener rapidement

4. 💡 CONSEILS PRATIQUES
   - Recommandations concrètes
   - Optimisations fiscales légales

Réponds de façon claire, structurée et professionnelle.
Mentionne toujours les sources officielles.
        """

        analyse = appel_mistral(prompt)

        # Ajouter les liens sources en bas
        liens = "\n\n---\n### 🔗 Sources officielles consultées :\n"
        sources_vues = set()
        for art in articles[:10]:
            if art['source'] not in sources_vues:
                liens += f"- **{art['source']}** : [{art['titre']}]({art['lien']})\n"
                sources_vues.add(art['source'])

        return analyse + liens

    except Exception as e:
        return f"Erreur veille fiscale : {e}"