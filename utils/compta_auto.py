import json
from utils.ai import appel_mistral

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

- nature_operation : type d'achat (ex : petit matériel, prestation, abonnement, immobilisation…)
- fournisseur : nom du fournisseur
- date_facture : format YYYY-MM-DD
- numero_facture : numéro détecté
- montant_ht
- montant_tva
- montant_ttc
- taux_tva

- comptes :
    - compte_charge_ou_immobilisation
    - compte_tva
    - compte_fournisseur

- ecriture_comptable : liste d'écritures au format :
    [
        {{
            "journal": "ACH",
            "date": "YYYY-MM-DD",
            "compte": "606300",
            "libelle": "Achat - {fournisseur}",
            "debit": 120.00,
            "credit": 0.00,
            "piece": "{numero_facture}"
        }},
        ...
    ]

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

