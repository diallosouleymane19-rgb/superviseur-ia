import pandas as pd
from .ai import appel_mistral

def analyser_alertes(df):
    """
    Analyse et alertes de gestion.
    """
    try:
        apercu = df.head(50).to_string()

        prompt = f"""
Tu es un expert-comptable français spécialisé en gestion et contrôle financier.

Analyse ce tableau financier et génère des alertes de gestion :

{apercu}

Génère un rapport d'alertes complet :

1. 🚨 ALERTES CRITIQUES
   - Seuils dépassés (dépenses anormales, TVA)
   - Factures impayées détectées
   - Soldes négatifs anormaux
   - Risques de trésorerie immédiats

2. ⚠️ ALERTES IMPORTANTES
   - Ratios financiers anormaux
   - Charges inhabituellement élevées
   - Marges dégradées
   - Délais de paiement dépassés

3. 📊 INDICATEURS DE GESTION
   - Ratio de liquidité
   - Délai moyen de paiement
   - Taux de charges
   - Évolution des principaux postes

4. 💡 RECOMMANDATIONS IMMÉDIATES
   - Actions prioritaires à mener
   - Décisions de gestion suggérées
   - Points de vigilance

5. 📅 ÉCHÉANCES À SURVEILLER
   - Déclarations fiscales à venir
   - Paiements urgents
   - Obligations comptables

Réponds de façon claire, structurée et professionnelle avec des emojis pour les alertes.
        """
        return appel_mistral(prompt)
    except Exception as e:
        return f"Erreur alertes : {e}"