import json
from utils.ai import appel_mistral

# ---------------------------------------------------------
# ANALYSE FACTURE PREMIUM (déjà existant)
# ---------------------------------------------------------
def analyse_facture_premium(contenu_facture):
    """
    Analyse IA PREMIUM :
    - Détection nature dépense
    - Comptes comptables
    - TVA
    - Écriture comptable exportable
    - Justification professionnelle
    """

    prompt = f"""
Tu es un expert-comptable français. Analyse la facture suivante :

{contenu_facture}

Retourne un JSON STRICT avec les champs suivants :

- nature_operation
- fournisseur
- date_facture
- numero_facture
- montant_ht
- montant_tva
- montant_ttc
- taux_tva

- comptes :
    - compte_charge_ou_immobilisation
    - compte_tva
    - compte_fournisseur

- ecriture_comptable : liste d'écritures

- justification :
    - pourquoi ces comptes
    - cohérence TVA
    - risques fiscaux
    - anomalies possibles

Réponds UNIQUEMENT en JSON valide.
    """

    reponse = appel_mistral(prompt)

    try:
        return json.loads(reponse)
    except:
        return {"erreur": "Impossible de parser la réponse IA", "raw": reponse}


# ---------------------------------------------------------
# 🔥 ANALYSE BALANCE (fonction manquante)
# ---------------------------------------------------------
def analyse_balance_ai(df):
    """
    Analyse IA de la balance comptable.
    Retourne un texte ou un JSON selon ton besoin.
    """

    # Convertir la balance en texte lisible pour l'IA
    balance_txt = df.to_string()

    prompt = f"""
Tu es un expert-comptable français. Analyse la balance suivante :

{balance_txt}

Donne une analyse structurée comprenant :
- points forts
- anomalies
- comptes à surveiller
- suggestions de régularisation
- risques fiscaux
- cohérence des soldes
- remarques professionnelles

Réponds en texte clair, structuré et professionnel.
    """

    reponse = appel_mistral(prompt)
    return reponse
