from .database import lister_analyses, get_analyse, get_client
from datetime import datetime

def generer_rapport_client(client_id):
    """
    Génère un rapport HTML complet pour un client.
    """
    client = get_client(client_id)
    analyses = lister_analyses(client_id)

    if not client:
        return "<p>Client introuvable.</p>"

    nom_client = client[1]
    siret = client[2] or "Non renseigné"
    secteur = client[3] or "Non renseigné"
    contact = client[4] or "Non renseigné"
    email = client[5] or "Non renseigné"
    date_creation = client[6]
    date_rapport = datetime.now().strftime("%d/%m/%Y")

    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Dossier client — {nom_client}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
            h1 {{ color: #1f77b4; border-bottom: 3px solid #1f77b4; padding-bottom: 10px; }}
            h2 {{ color: #1f77b4; margin-top: 40px; }}
            h3 {{ color: #444; }}
            .info-box {{ background: #f0f4ff; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            .analyse-box {{ background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #1f77b4; }}
            .badge {{ background: #1f77b4; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; }}
            .footer {{ margin-top: 60px; text-align: center; color: #999; font-size: 12px; }}
            pre {{ white-space: pre-wrap; font-family: Arial, sans-serif; }}
        </style>
    </head>
    <body>
        <h1>📁 Dossier Client — {nom_client}</h1>
        <p><em>Rapport généré le {date_rapport} par SMD Consulting — Superviseur IA Comptable</em></p>

        <div class="info-box">
            <h2>📋 Informations Client</h2>
            <p><strong>Nom :</strong> {nom_client}</p>
            <p><strong>SIRET :</strong> {siret}</p>
            <p><strong>Secteur :</strong> {secteur}</p>
            <p><strong>Contact :</strong> {contact}</p>
            <p><strong>Email :</strong> {email}</p>
            <p><strong>Dossier créé le :</strong> {date_creation}</p>
            <p><strong>Nombre d'analyses :</strong> {len(analyses)}</p>
        </div>

        <h2>📊 Historique des Analyses</h2>
    """

    if not analyses:
        html += "<p>Aucune analyse enregistrée pour ce client.</p>"
    else:
        for analyse in analyses:
            analyse_id = analyse[0]
            type_analyse = analyse[1]
            titre = analyse[2]
            date_analyse = analyse[3]
            exercice = analyse[4] or ""

            detail = get_analyse(analyse_id)
            contenu = detail[4] if detail else ""

            html += f"""
        <div class="analyse-box">
            <h3>{type_analyse} — {titre}</h3>
            <p>
                <span class="badge">{type_analyse}</span>
                &nbsp; 📅 {date_analyse}
                {"&nbsp; 📆 Exercice : " + exercice if exercice else ""}
            </p>
            <hr>
            <pre>{contenu}</pre>
        </div>
            """

    html += f"""
        <div class="footer">
            <p>© {datetime.now().year} SMD Consulting — Superviseur IA Comptable</p>
            <p>Document confidentiel — Usage professionnel uniquement</p>
        </div>
    </body>
    </html>
    """

    return html