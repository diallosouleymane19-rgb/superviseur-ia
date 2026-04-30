from datetime import datetime

def obtenir_veille_fiscale():
    """
    Retourne (texte_markdown, html)
    """
    articles = [
        {
            "source": "Journal Officiel",
            "titre": "Seuils micro-entrepreneurs 2026 : revalorisation de 5%",
            "impact": "Les seuils de TVA et de chiffre d'affaires augmentent de 5%.",
            "action": "Vérifier les seuils de vos clients avant le 31 mai 2026.",
            "lien": "https://www.legifrance.gouv.fr/jorf/jo"
        },
        {
            "source": "BOFiP",
            "titre": "TVA : précisions sur les livraisons à soi-même (LAS)",
            "impact": "Les entreprises réalisant des LAS doivent utiliser le formulaire 3310-LAS.",
            "action": "Identifier les clients concernés (BTP, travaux).",
            "lien": "https://bofip.impots.gouv.fr/bofip"
        },
        {
            "source": "URSSAF",
            "titre": "Échéances sociales mai 2026",
            "impact": "Paiement des cotisations sociales le 15 mai, DSN le 10 mai.",
            "action": "Programmer les rappels clients avant le 10 mai.",
            "lien": "https://www.urssaf.fr"
        }
    ]

    md = f"📰 **Veille fiscale – semaine du {datetime.now().strftime('%d/%m/%Y')}**\n\n"
    md += "*Généré par IA – SMD Consulting*\n\n---\n\n"

    for a in articles:
        md += f"### 📌 {a['titre']}\n"
        md += f"- **Source :** {a['source']}\n"
        md += f"- **Impact :** {a['impact']}\n"
        md += f"- **Action :** {a['action']}\n"
        md += f"- [📖 Lire l'article]({a['lien']})\n\n---\n\n"

    html = f"""
    <html>
    <head><meta charset="UTF-8"><title>Veille fiscale</title></head>
    <body>
        <h1>📰 Veille fiscale – {datetime.now().strftime('%d/%m/%Y')}</h1>
        <hr>
    """
    for a in articles:
        html += f"<h3>📌 {a['titre']}</h3><p><strong>Impact :</strong> {a['impact']}</p><p><strong>Action :</strong> {a['action']}</p><hr>"
    html += "</body></html>"

    return md, html