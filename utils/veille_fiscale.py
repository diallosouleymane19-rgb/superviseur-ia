import feedparser
from .ai import appel_mistral
from datetime import datetime

SOURCES_RSS = [
    "https://www.economie.gouv.fr/rss.xml",
    "https://www.urssaf.fr/portail/home/rss.rss",
    "https://bofip.impots.gouv.fr/bofip/flux-rss.html",
]

def recuperer_articles_rss():
    articles = []
    for url in SOURCES_RSS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                articles.append({
                    "source": feed.feed.get("title", url),
                    "titre": entry.get("title", "Sans titre"),
                    "lien": entry.get("link", ""),
                    "date": entry.get("published", ""),
                    "resume": entry.get("summary", "")[:300]
                })
        except Exception:
            continue
    return articles

def obtenir_veille_fiscale():
    try:
        date_jour = datetime.now().strftime("%d/%m/%Y")
        articles = recuperer_articles_rss()

        if articles:
            contexte = ""
            for art in articles:
                contexte += f"Source: {art['source']}\nTitre: {art['titre']}\nDate: {art['date']}\nRésumé: {art['resume']}\n---\n"
        else:
            contexte = "Les flux RSS officiels ne sont pas disponibles actuellement."

        prompt = f"""
Tu es un expert fiscaliste français. Nous sommes le {date_jour}.

{f"Voici les dernières actualités officielles récupérées :{contexte}" if articles else "Génère une veille fiscale complète et à jour pour les entreprises françaises."}

Génère une veille fiscale structurée en Markdown propre :

## 📋 Actualités fiscales récentes
- Points législatifs importants avec sources

## 📅 Calendrier fiscal de mai 2026
- Échéances et obligations du mois

## 💼 Impact pour les entreprises
- Ce que les PME/TPE doivent savoir

## 💡 Conseils pratiques
- Recommandations concrètes et optimisations légales

Réponds uniquement en Markdown propre, sans caractères d'échappement.
        """

        return appel_mistral(prompt)

    except Exception as e:
        return f"Erreur veille fiscale : {e}"