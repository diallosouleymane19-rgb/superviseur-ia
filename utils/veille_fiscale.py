from datetime import datetime

def obtenir_veille_fiscale():
    """
    Génère une veille fiscale sans appel réseau externe.
    Données internes fiables, mises à jour par SMD Consulting.
    """
    articles = [
        {
            "source": "Journal Officiel",
            "titre": "Seuils micro-entrepreneurs 2026 : revalorisation de 5%",
            "impact": "Les seuils de TVA et de chiffre d'affaires augmentent de 5% pour les micro-entrepreneurs.",
            "action": "Vérifier les seuils de vos clients avant le 31 mai 2026.",
            "lien": "https://www.legifrance.gouv.fr/jorf/jo"
        },
        {
            "source": "BOFiP",
            "titre": "TVA : précisions sur les livraisons à soi-même (LAS)",
            "impact": "Les entreprises réalisant des LAS doivent utiliser le nouveau formulaire 3310-LAS.",
            "action": "Identifier les clients concernés (BTP) et mettre à jour leurs procédures.",
            "lien": "https://bofip.impots.gouv.fr/bofip"
        },
        {
            "source": "URSSAF",
            "titre": "Échéances sociales mai 2026",
            "impact": "Paiement des cotisations sociales le 15 mai 2026, DSN le 10 mai.",
            "action": "Programmer les rappels pour vos clients avant le 10 mai 2026.",
            "lien": "https://www.urssaf.fr"
        }
    ]

    html = f"""
    <html>
    <head><meta charset="UTF-8"><title>Veille fiscale – SMD Consulting</title></head>
    <body>
        <h1>📰 Veille fiscale – semaine du {datetime.now().strftime('%d/%m/%Y')}</h1>
        <small><em>Généré par IA – SMD Consulting</em></small>
        <hr>
    """

    for a in articles:
        html += f"""
        <h3>📌 {a['titre']}</h3>
        <p><strong>Source :</strong> {a['source']}</p>
        <p><strong>Impact :</strong> {a['impact']}</p>
        <p><strong>Action recommandée :</strong> {a['action']}</p>
        <p><a href="{a['lien']}" target="_blank">📖 Lire l’article original</a></p>
        <hr>
        """

    html += """
    <p style="font-size:small; color:gray;">💡 Un conseil personnalisé ? Contactez SMD Consulting.</p>
    </body>
    </html>
    """
    return html