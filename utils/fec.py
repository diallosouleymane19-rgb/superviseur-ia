import pandas as pd
from .ai import appel_mistral

def generer_fec():
    import datetime
    filename = f"FEC_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("Journal\tDate\tCompte\tLibellé\tDébit\tCrédit\n")
        f.write("AC\t20240101\t606\tAchat fournitures\t100.00\t0.00\n")
    return filename

def traiter_fec(fichier):
    """
    Lecture et analyse IA du fichier FEC.
    """
    try:
        # Lecture du fichier FEC (séparateur tabulation)
        df = pd.read_csv(fichier, sep="\t", dtype=str)

        # Limiter pour éviter un prompt trop long
        apercu = df.head(50).to_string()

        prompt = f"""
Tu es un expert-comptable français spécialisé en contrôle fiscal.
Analyse ce fichier FEC (Fichier des Écritures Comptables) :

{apercu}

Donne une analyse structurée comprenant :
- Cohérence des écritures comptables
- Anomalies ou irrégularités détectées
- Comptes les plus utilisés
- Risques fiscaux potentiels
- Recommandations de régularisation
- Remarques professionnelles

Réponds en texte clair, structuré et professionnel.
        """

        analyse = appel_mistral(prompt)
        return analyse

    except Exception as e:
        return f"Erreur lors du traitement du FEC : {e}"