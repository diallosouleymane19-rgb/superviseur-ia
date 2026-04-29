import pandas as pd
from .ai import appel_mistral

def analyser_coherence(df_factures=None, df_balance=None, df_fec=None):
    """
    Analyse de cohérence inter-documents.
    """
    try:
        contexte = ""

        if df_factures is not None:
            contexte += f"\nFACTURES :\n{df_factures.head(20).to_string()}\n"

        if df_balance is not None:
            contexte += f"\nBALANCE COMPTABLE :\n{df_balance.head(20).to_string()}\n"

        if df_fec is not None:
            contexte += f"\nFICHIER FEC :\n{df_fec.head(20).to_string()}\n"

        prompt = f"""
Tu es un expert-comptable français spécialisé en contrôle interne.

Voici les documents comptables à analyser :
{contexte}

Effectue une analyse de cohérence inter-documents complète :

1. COHÉRENCE DES MONTANTS
   - Les montants des factures correspondent-ils à la balance ?
   - Les écritures FEC sont-elles cohérentes avec les factures ?
   - Vérification des totaux et sous-totaux

2. COHÉRENCE DES DATES
   - Les dates des factures correspondent-elles aux écritures ?
   - Exercices comptables respectés ?
   - Coupures d'exercice correctes ?

3. COHÉRENCE DES TIERS
   - Les fournisseurs/clients sont-ils cohérents entre documents ?
   - Comptes tiers correctement imputés ?

4. ANOMALIES DÉTECTÉES
   - Écarts significatifs entre documents
   - Données manquantes ou incohérentes
   - Doublons inter-documents

5. RISQUES ET RECOMMANDATIONS
   - Risques fiscaux identifiés
   - Actions correctives prioritaires
   - Points de contrôle à renforcer

Réponds de façon claire, structurée et professionnelle.
        """
        return appel_mistral(prompt)
    except Exception as e:
        return f"Erreur cohérence : {e}"