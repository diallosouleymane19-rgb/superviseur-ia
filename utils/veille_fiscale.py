from .ai import appel_mistral

def obtenir_veille_fiscale():
    """
    Veille fiscale et réglementaire française.
    """
    try:
        prompt = """
Tu es un expert fiscaliste français parfaitement à jour sur la réglementation fiscale française.

Génère une veille fiscale complète et structurée pour les entreprises françaises :

1. 📋 ACTUALITÉS FISCALES RÉCENTES
   - Dernières modifications législatives
   - Nouveaux textes fiscaux importants
   - Jurisprudences récentes significatives

2. 📅 CALENDRIER FISCAL DU MOMENT
   - Déclarations TVA à venir (CA3, CA12)
   - Acomptes IS (Impôt sur les Sociétés)
   - Déclarations de résultats
   - Taxes et contributions sociales
   - DSN (Déclaration Sociale Nominative)

3. 💼 POINTS DE VIGILANCE ENTREPRISES
   - Contrôles fiscaux fréquents actuellement
   - Zones de risque à surveiller
   - Nouvelles obligations déclaratives

4. 🔄 CHANGEMENTS RÉGLEMENTAIRES
   - Taux de TVA modifiés
   - Nouveaux seuils et plafonds
   - Modifications des régimes fiscaux
   - Nouvelles exonérations ou déductions

5. 💡 CONSEILS PRATIQUES
   - Optimisations fiscales légales du moment
   - Dispositifs d'aide aux entreprises
   - Bonnes pratiques comptables et fiscales

6. 🌍 FISCALITÉ INTERNATIONALE
   - Conventions fiscales récentes
   - Règles de TVA intracommunautaire
   - Prix de transfert et obligations

Réponds de façon claire, structurée et professionnelle.
        """
        return appel_mistral(prompt)
    except Exception as e:
        return f"Erreur veille fiscale : {e}"