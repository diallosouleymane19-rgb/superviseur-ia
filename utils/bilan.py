import pandas as pd
from .ai import appel_mistral

def analyser_bilan(df):
    """
    Analyse IA du bilan comptable.
    """
    try:
        apercu = df.head(50).to_string()

        prompt = f"""
Tu es un expert-comptable français spécialisé en analyse financière.

Analyse ce bilan comptable :

{apercu}

Donne une analyse complète et structurée :

1. STRUCTURE DU BILAN
   - Analyse de l'Actif (immobilisations, stocks, créances, trésorerie)
   - Analyse du Passif (capitaux propres, dettes financières, dettes fournisseurs)
   - Équilibre Actif/Passif

2. RATIOS FINANCIERS CLÉS
   - Ratio de liquidité générale (Actif circulant / Dettes CT)
   - Ratio de liquidité réduite
   - Ratio d'autonomie financière (Capitaux propres / Total passif)
   - Ratio d'endettement
   - Ratio de solvabilité

3. FONDS DE ROULEMENT
   - Fonds de Roulement Net Global (FRNG)
   - Besoin en Fonds de Roulement (BFR)
   - Trésorerie Nette (TN = FRNG - BFR)
   - Interprétation et recommandations

4. ANALYSE DE LA STRUCTURE FINANCIÈRE
   - Solidité financière
   - Capacité d'endettement
   - Risques financiers identifiés

5. POINTS FORTS ET POINTS FAIBLES
   - Atouts du bilan
   - Faiblesses et risques
   - Comparaison avec les normes sectorielles

6. RECOMMANDATIONS
   - Actions correctives prioritaires
   - Optimisations financières suggérées
   - Risques fiscaux et comptables

Réponds de façon claire, structurée et professionnelle.
        """
        return appel_mistral(prompt)
    except Exception as e:
        return f"Erreur analyse bilan : {e}"