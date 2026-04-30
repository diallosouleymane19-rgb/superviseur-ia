import pandas as pd
from .ai import appel_mistral

def analyser_bilan(df):
    try:
        apercu = df.head(50).to_string()
        return analyser_bilan_texte(apercu)
    except Exception as e:
        return f"Erreur analyse bilan : {e}"

def analyser_bilan_texte(texte):
    try:
        prompt = f"""
Tu es un expert-comptable français spécialisé en analyse financière.

Analyse ce bilan comptable :

{texte}

Donne une analyse complète :
1. STRUCTURE DU BILAN (Actif/Passif)
2. RATIOS FINANCIERS (liquidité, autonomie, endettement, solvabilité)
3. FONDS DE ROULEMENT (FRNG, BFR, Trésorerie Nette)
4. ANALYSE DE LA STRUCTURE FINANCIÈRE
5. POINTS FORTS ET POINTS FAIBLES
6. RECOMMANDATIONS

Réponds de façon claire, structurée et professionnelle.
        """
        return appel_mistral(prompt)
    except Exception as e:
        return f"Erreur analyse bilan : {e}"