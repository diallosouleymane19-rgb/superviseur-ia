import pandas as pd
from .ai import appel_mistral

def rapprocher_banque_compta(df_banque, df_compta):
    """
    Rapprochement entre relevé bancaire et écritures comptables.
    """
    try:
        apercu_banque = df_banque.head(30).to_string()
        apercu_compta = df_compta.head(30).to_string()

        prompt = f"""
Tu es un expert-comptable français spécialisé en rapprochement bancaire.

RELEVÉ BANCAIRE :
{apercu_banque}

ÉCRITURES COMPTABLES :
{apercu_compta}

Effectue un rapprochement bancaire complet :

1. OPÉRATIONS RAPPROCHÉES
   - Liste des opérations qui concordent (même montant, même date)

2. ÉCARTS DÉTECTÉS
   - Opérations présentes en banque mais absentes en comptabilité
   - Opérations présentes en comptabilité mais absentes en banque
   - Différences de montants

3. ANALYSE DES ÉCARTS
   - Causes probables des écarts
   - Opérations en transit
   - Erreurs potentielles

4. RECOMMANDATIONS
   - Actions correctives à mener
   - Écritures de régularisation suggérées
   - Risques identifiés

Réponds de façon claire, structurée et professionnelle.
        """
        return appel_mistral(prompt)
    except Exception as e:
        return f"Erreur rapprochement : {e}"