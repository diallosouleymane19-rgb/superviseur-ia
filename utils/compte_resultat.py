import pandas as pd
from .ai import appel_mistral

def analyser_compte_resultat(df):
    try:
        apercu = df.head(50).to_string()
        return analyser_cr_texte(apercu)
    except Exception as e:
        return f"Erreur analyse compte de résultat : {e}"

def analyser_cr_texte(texte):
    try:
        prompt = f"""
Tu es un expert-comptable français spécialisé en analyse financière.

Analyse ce compte de résultat :

{texte}

Donne une analyse complète :
1. SOLDES INTERMÉDIAIRES DE GESTION (SIG)
   - Chiffre d'affaires
   - Marge commerciale
   - Valeur Ajoutée (VA)
   - Excédent Brut d'Exploitation (EBE)
   - Résultat d'exploitation
   - Résultat net

2. ANALYSE DES PRODUITS
   - Structure et évolution du CA
   - Autres produits significatifs

3. ANALYSE DES CHARGES
   - Charges d'exploitation
   - Charges financières
   - Charges exceptionnelles
   - Poids des charges par rapport au CA

4. RATIOS DE RENTABILITÉ
   - Taux de marge brute
   - Taux de marge nette
   - Taux de valeur ajoutée
   - Rentabilité économique et financière

5. POINTS FORTS ET POINTS FAIBLES
6. RECOMMANDATIONS

Réponds de façon claire, structurée et professionnelle.
        """
        return appel_mistral(prompt)
    except Exception as e:
        return f"Erreur analyse compte de résultat : {e}"