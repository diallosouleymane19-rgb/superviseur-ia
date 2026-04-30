import pandas as pd
from .ai import appel_mistral

def analyser_compte_resultat(df):
    """
    Analyse IA du compte de résultat.
    """
    try:
        apercu = df.head(50).to_string()

        prompt = f"""
Tu es un expert-comptable français spécialisé en analyse financière.

Analyse ce compte de résultat :

{apercu}

Donne une analyse complète et structurée :

1. SOLDES INTERMÉDIAIRES DE GESTION (SIG)
   - Chiffre d'affaires (CA)
   - Marge commerciale
   - Production de l'exercice
   - Valeur Ajoutée (VA)
   - Excédent Brut d'Exploitation (EBE)
   - Résultat d'exploitation
   - Résultat courant avant impôts
   - Résultat net

2. ANALYSE DES PRODUITS
   - Structure des produits
   - Évolution du chiffre d'affaires
   - Autres produits significatifs

3. ANALYSE DES CHARGES
   - Charges d'exploitation (achats, salaires, loyers)
   - Charges financières
   - Charges exceptionnelles
   - Poids des charges par rapport au CA

4. RATIOS DE RENTABILITÉ
   - Taux de marge brute
   - Taux de marge nette
   - Taux de valeur ajoutée
   - Rentabilité économique
   - Rentabilité financière

5. POINTS FORTS ET POINTS FAIBLES
   - Performances remarquables
   - Postes de charges excessifs
   - Risques sur la rentabilité

6. RECOMMANDATIONS
   - Optimisation des charges
   - Axes d'amélioration de la rentabilité
   - Risques fiscaux identifiés
   - Actions prioritaires

Réponds de façon claire, structurée et professionnelle.
        """
        return appel_mistral(prompt)
    except Exception as e:
        return f"Erreur analyse compte de résultat : {e}"